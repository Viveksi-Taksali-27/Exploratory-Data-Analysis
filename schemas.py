from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RecordBase(BaseModel):
    name: str
    age: int
    salary: float
    department: str
    experience: int

class RecordCreate(RecordBase):
    pass

class RecordUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    salary: Optional[float] = None
    department: Optional[str] = None
    experience: Optional[int] = None

class RecordInDB(RecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True