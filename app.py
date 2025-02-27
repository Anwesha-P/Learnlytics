import streamlit as st
import pandas as pd
import os
import re

# Create directories if they do not exist
UPLOAD_FOLDER = "uploads"
OUTPUT_FILE = "slo_grades.csv"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def process_csv(grades_path, questions_path, output_path):
    grades_df = pd.read_csv(grades_path)
    questions_df = pd.read_csv(questions_path, header=2)
    
    # Keep necessary columns
    questions_df = questions_df[["Q#", "Question name"]]
    questions_df.columns = questions_df.columns.str.strip()
    grades_df.columns = grades_df.columns.str.strip()
    
    # Identify question response columns
    response_columns = [col for col in grades_df.columns if col.startswith("Q.")]    
    
    # Extract total marks from column titles
    total_marks = {col: float(re.search(r'/([0-9]+\.?[0-9]*)', col).group(1)) if re.search(r'/([0-9]+\.?[0-9]*)', col) else 1 for col in response_columns}
    
    # Transform grades data
    responses_melted = grades_df.melt(
        id_vars=["Last name", "First name", "ID number", "Email address"],
        value_vars=response_columns,
        var_name="Response Type",
        value_name="Response"
    )

    responses_melted["Q#"] = responses_melted["Response Type"].str.extract(r'(\d+)').astype(float).astype('Int64')
    merged_df = responses_melted.merge(questions_df, on="Q#", how="left")

    # Filter questions containing "SLO"
    merged_df["Question name"] = merged_df["Question name"].str.strip()
    slo_questions_df = merged_df[merged_df["Question name"].str.contains("SLO", case=False, na=False)]
    slo_question_numbers = slo_questions_df["Q#"].unique()

    slo_response_columns = [col for col in grades_df.columns if any(col.startswith(f"Q. {int(q)}") for q in slo_question_numbers)]
    
    # Rename columns based on SLO names from the questions file
    slo_column_mapping = {col: re.search(r'SLO \d+', slo_questions_df.loc[slo_questions_df["Q#"] == int(col.split()[1]), "Question name"].values[0]).group(0) for col in slo_response_columns}
    
    # Convert grades to percentages based on total marks
    for col in slo_response_columns:
        grades_df[col] = pd.to_numeric(grades_df[col], errors='coerce')
        grades_df[col] = (grades_df[col] / total_marks[col]) * 100  # Convert to percentage
        grades_df[col] = grades_df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")

    slo_grades_df = grades_df[["Last name", "First name", "ID number", "Email address"] + slo_response_columns].rename(columns=slo_column_mapping)
    slo_grades_df.to_csv(output_path, index=False)

def main():
    st.title("Learlytics: Moodle Grades to SLO processing")

    st.write("Upload the two CSV files (grades and questions) from Moodle for processing.")
    
    # Input fields for course, section, academic period
    col1, col2, col3 = st.columns(3)
    with col1:
        course = st.text_input("Course", placeholder="Eg: BUS 205")
    with col2:
        section = st.text_input("Section", placeholder="Eg: A")
    with col3:
        academic_period = st.text_input("Academic Period", placeholder="Eg: Spring 2025")

    # Upload CSV files
    file1 = st.file_uploader("Upload the CSV file from the 'Grades' report on Moodle", type=["csv"])
    file2 = st.file_uploader("Upload the CSV file from the 'Questions Statistics' report on Moodle", type=["csv"])
    
    if file1 and file2:
        # Save files locally
        file1_path = os.path.join(UPLOAD_FOLDER, "grades.csv")
        file2_path = os.path.join(UPLOAD_FOLDER, "questions.csv")

        with open(file1_path, "wb") as f:
            f.write(file1.getbuffer())
        
        with open(file2_path, "wb") as f:
            f.write(file2.getbuffer())

        try:
            # Process the uploaded files
            process_csv(file1_path, file2_path, OUTPUT_FILE)
            st.success("Files processed successfully! Click below to download the result.")
            
            # Create output file name
            output_file = f"{course.replace(' ', '_')}-{section.replace(' ', '_')}-{academic_period.replace(' ', '_')}.csv"
            
            # Open the generated file and provide the download button
            with open(OUTPUT_FILE, "rb") as f:
                st.download_button("Download SLO Grades", f, file_name=output_file)

        except Exception as e:
            st.error(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
