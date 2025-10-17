# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from requests.exceptions import RequestException
import json
import io

# Configuration
API_URL = "http://localhost:8000"

def fetch_analysis():
    response = requests.get(f"{API_URL}/analyze/")
    
    if response.status_code == 200:
        return response.json()
    else:
        st.warning("No data available for analysis. Please upload a CSV file.")
        return None

def check_api_health():
    try:
        response = requests.get(f"{API_URL}/")
        return response.status_code == 200
    except RequestException:
        return False

def create_record(data):
    response = requests.post(f"{API_URL}/records/", json=data)
    return response.json() if response.status_code == 200 else None

def update_record(record_id, data):
    response = requests.put(f"{API_URL}/records/{record_id}", json=data)
    return response.json() if response.status_code == 200 else None

def delete_record(record_id):
    response = requests.delete(f"{API_URL}/records/{record_id}")
    return response.status_code == 200

def get_records(page, per_page):
    response = requests.get(f"{API_URL}/records/", params={"page": page, "per_page": per_page})
    return response.json() if response.status_code == 200 else None

def analyze_data():
    response = requests.get(f"{API_URL}/analyze/")
    print(response)
    return response.json() if response.status_code == 200 else None

def main():
    st.set_page_config(page_title="Data Analysis Dashboard", layout="wide")
    
    st.title("Data Analysis Dashboard")
    
    if not check_api_health():
        st.error("⚠️ Cannot connect to the backend API. Please ensure the FastAPI backend is running.")
        return

    # Sidebar navigation
    page = st.sidebar.selectbox("Navigation", ["Data Management", "Data Analysis"])

    if page == "Data Management":
        st.header("Data Management")
        
        # File upload section
        uploaded_file = st.file_uploader("Upload CSV file", type="csv")
        if uploaded_file:
            # Read file content
            file_bytes = uploaded_file.getvalue()

            # Send the file correctly formatted
            files = {"file": ("uploaded.csv", file_bytes, "text/csv")}

            response = requests.post(f"{API_URL}/upload-csv/", files=files)

            if response.status_code == 200:
                st.success("File uploaded successfully!")
            else:
                st.error(f"Error uploading file: {response.text}")  # Print full error response
                
        # CRUD Operations
        crud_operation = st.selectbox("Select Operation", ["View Records", "Add Record", "Edit Record", "Delete Record"])

        if crud_operation == "View Records":
            page_number = st.number_input("Page", min_value=1, value=1)
            records = get_records(page_number, 10)
            
            if records:
                st.write(f"Showing page {records['page']} of {records['total_pages']}")
                st.table(pd.DataFrame(records['records']))
            else:
                st.warning("No records found")

        elif crud_operation == "Add Record":
            with st.form("add_record"):
                name = st.text_input("Name")
                age = st.number_input("Age", min_value=0)
                salary = st.number_input("Salary", min_value=0.0)
                department = st.text_input("Department")
                experience = st.number_input("Experience (years)", min_value=0)
                
                if st.form_submit_button("Add Record"):
                    record = {
                        "name": name,
                        "age": age,
                        "salary": salary,
                        "department": department,
                        "experience": experience
                    }
                    if create_record(record):
                        st.success("Record added successfully!")
                    else:
                        st.error("Error adding record")

        elif crud_operation == "Edit Record":
            record_id = st.number_input("Enter Record ID to Edit", min_value=0)
            with st.form("edit_record"):
                name = st.text_input("Name (leave blank to keep unchanged)")
                age = st.number_input("Age (leave blank to keep unchanged)", min_value=0)
                salary = st.number_input("Salary (leave blank to keep unchanged)", min_value=0.0)
                department = st.text_input("Department (leave blank to keep unchanged)")
                experience = st.number_input("Experience (leave blank to keep unchanged)", min_value=0)
                
                if st.form_submit_button("Update Record"):
                    update_data = {}
                    if name: update_data["name"] = name
                    if age: update_data["age"] = age
                    if salary: update_data["salary"] = salary
                    if department: update_data["department"] = department
                    if experience: update_data["experience"] = experience
                    
                    if update_record(record_id, update_data):
                        st.success("Record updated successfully!")
                    else:
                        st.error("Error updating record")

        elif crud_operation == "Delete Record":
            record_id = st.number_input("Enter Record ID to Delete", min_value=0)
            if st.button("Delete Record"):
                if delete_record(record_id):
                    st.success("Record deleted successfully!")
                else:
                    st.error("Error deleting record")

    else:  # Data Analysis page
        st.header("Data Analysis")
        
        analysis_results = analyze_data()
        if not analysis_results:
            st.warning("No data available for analysis. Please upload a CSV file first.")
            return

        # Display basic information
        st.subheader("Dataset Overview")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Rows", analysis_results["basic_info"]["total_rows"])
        col2.metric("Total Columns", analysis_results["basic_info"]["total_columns"])
        col3.metric("Numeric Columns", analysis_results["basic_info"]["numeric_columns"])
        col4.metric("Categorical Columns", analysis_results["basic_info"]["categorical_columns"])

        # Analysis Tabs
        tab1, tab2, tab3 = st.tabs(["Numeric Analysis", "Categorical Analysis", "Missing Values"])
        

        with tab1:
            st.subheader("Numeric Columns Analysis")

            if analysis_results.get("numeric_stats"):
                numeric_col = st.selectbox(
                    "Select numeric column for analysis",
                    list(analysis_results["numeric_stats"].keys())
                )

        # Display Statistics
        stats = analysis_results["numeric_stats"][numeric_col]
        st.write(f"Mean: {stats['mean']}")
        st.write(f"Median: {stats['median']}")
        st.write(f"Standard Deviation: {stats['std']}")
        st.write(f"Min: {stats['min']}")
        st.write(f"Max: {stats['max']}")

            # 🔹 Histogram for Numeric Column
        st.subheader(f"Histogram of {numeric_col}")
        # Use only the first len(hist_values) elements of bin_edges for x
        hist_fig = px.bar(
            x=stats["histogram_bins"][:-1],  # Use all but the last bin edge
            y=stats["histogram_values"],
            labels={"x": numeric_col, "y": "Frequency"},
            title=f"Histogram of {numeric_col}",
        )
        st.plotly_chart(hist_fig)

        # 🔹 Pie Chart for Numeric Column Distribution
        st.subheader(f"Pie Chart of {numeric_col}")
        pie_fig = px.pie(
            values=stats["histogram_values"],
            names=[f"Bin {i+1}" for i in range(len(stats["histogram_values"]))],  # Use the length of histogram_values
            title=f"{numeric_col} Distribution"
        )
        st.plotly_chart(pie_fig)
  

        with tab2:
            st.subheader("Categorical Columns Analysis")
    
            if analysis_results.get("categorical_stats"):
                cat_col = st.selectbox(
                    "Select column for analysis",
                    list(analysis_results["categorical_stats"].keys())
                )

        if "labels" in analysis_results["categorical_stats"][cat_col]:
            labels = analysis_results["categorical_stats"][cat_col]["labels"]
            values = analysis_results["categorical_stats"][cat_col]["values"]

            # 🔵 Bar Chart
            st.subheader(f"Bar Chart of {cat_col}")
            bar_fig = px.bar(x=labels, y=values, labels={"x": cat_col, "y": "Count"}, title=f"{cat_col} Distribution")
            st.plotly_chart(bar_fig)

            # 🟠 Pie Chart
            st.subheader(f"Pie Chart of {cat_col}")
            pie_fig = px.pie(names=labels, values=values, title=f"{cat_col} Distribution")
            st.plotly_chart(pie_fig)


        with tab3:
            st.subheader("Missing Values Analysis")
            missing_data = pd.DataFrame.from_dict(
                analysis_results["missing_values"],
                orient='index',
                columns=['Missing Count']
            )
            st.dataframe(missing_data)

if __name__ == "__main__":
    main()