from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import io
import logging
import models
import schemas
from models import get_db, Record

# Create database tables
models.create_tables()
db=get_db()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Analysis API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"message": "API is running"}

@app.post("/upload-csv/")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)  # Add the database dependency
):
    try:
        # Read file content
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Insert data into PostgreSQL
        records = []
        for _, row in df.iterrows():
            record = Record(
                name=row["Name"],
                age=int(row["Age"]),
                salary=float(row["Salary"]),
                department=row["Department"],
                experience=int(row["Experience"]),
            )
            records.append(record)

        # Use the db session from the dependency
        db.add_all(records)
        db.commit()

        logger.info(f"File uploaded successfully with {len(df)} rows")
        return {
            "message": "File uploaded successfully!", 
            "rows_processed": len(df),
            "columns": df.columns.tolist()
        }
    except Exception as e:
        logger.error(f"Error in file upload: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Error processing file: {str(e)}"
        )
    

@app.get("/records/")
async def get_records(page: int = 1, per_page: int = 10, db: Session = Depends(get_db)):
    records = db.query(Record).offset((page - 1) * per_page).limit(per_page).all()
    total_records = db.query(Record).count()

    return {
        "records": records,
        "total": total_records,
        "page": page,
        "total_pages": (total_records + per_page - 1) // per_page
    }

@app.post("/records/")
async def create_record(record: schemas.RecordCreate, db: Session = Depends(get_db)):
    db_record = Record(**record.dict())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@app.put("/records/{record_id}")
async def update_record(record_id: int, record: schemas.RecordUpdate, db: Session = Depends(get_db)):
    db_record = db.query(Record).filter(Record.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Record not found")

    for key, value in record.dict(exclude_unset=True).items():
        setattr(db_record, key, value)

    db.commit()
    db.refresh(db_record)
    return db_record

@app.delete("/records/{record_id}")
async def delete_record(record_id: int, db: Session = Depends(get_db)):
    db_record = db.query(Record).filter(Record.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(db_record)
    db.commit()
    return {"message": "Record deleted successfully"}

from models import engine
import numpy as np


@app.get("/analyze/")
async def analyze_data():
    query = "SELECT * FROM records"
    
    try:
        # Execute the query and load the data into a DataFrame
        df = pd.read_sql_query(query, engine)
    except Exception as e:
        logger.error(f"Error querying the database: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")

    numeric_columns = df.select_dtypes(include=[np.number]).columns
    categorical_columns = df.select_dtypes(exclude=[np.number]).columns

    stats = {
        "basic_info": {
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "numeric_columns": int(len(numeric_columns)),
            "categorical_columns": int(len(categorical_columns)),
            "columns": list(df.columns)
        },
        "column_types": {col: str(df[col].dtype) for col in df.columns},
        "missing_values": {col: int(val) for col, val in df.isnull().sum().items()},
        "numeric_stats": {},
        "categorical_stats": {}
    }

    # Handle numeric columns
    if len(numeric_columns) > 0:
        for col in numeric_columns:
            hist_values, bin_edges = np.histogram(df[col].dropna(), bins=10)
            stats["numeric_stats"][col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "histogram_bins": [float(x) for x in bin_edges],
                "histogram_values": [int(x) for x in hist_values]
            }

    # Handle categorical columns
    if len(categorical_columns) > 0:
        for col in categorical_columns:
            value_counts = df[col].value_counts().head(10)
            stats["categorical_stats"][col] = {
                "value_counts": {str(k): int(v) for k, v in value_counts.items()},
                "unique_values": int(df[col].nunique()),
                "labels": [str(x) for x in value_counts.index],
                "values": [int(x) for x in value_counts.values]
            }

    logger.info(f"Analysis completed: {stats['basic_info']}")
    return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
