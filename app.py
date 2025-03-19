import streamlit as st
import pandas as pd
import os
import re
import webbrowser
import urllib.parse

# Create directories if they do not exist
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def open_outlook_web_email(subject, recipient=""):
    try:
        # URL encode the subject and body for safety
        subject_encoded = urllib.parse.quote(subject)
        body = "Please find the attached file."
        body_encoded = urllib.parse.quote(body)
        
        # Create the mailto link for Outlook Web App
        mailto_link = f"mailto:{recipient}?subject={subject_encoded}&body={body_encoded}"

        # Open the default web browser with the mailto link
        webbrowser.open(mailto_link)

        st.success("Opening Outlook Web App with the pre-filled email.")
    
    except Exception as e:
        st.error(f"Error opening Outlook Web: {e}")

def process_csv(grades_path, questions_path, output_path):
    grades_df = pd.read_csv(grades_path)
    questions_df = pd.read_csv(questions_path, header=2)
    
    # Remove the last row in grades_df only if it contains "Overall Average" in the "Last name" column
    if grades_df.iloc[-1]["Last name"] == "Overall average":
        grades_df = grades_df[:-1]
    
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
    st.title("Learnalytics: Moodle Grades to SLO Processing")

    st.write("Upload the CSV files (grades and questions) from Moodle. Files with matching names will be paired automatically.")
    
    # Input fields for course, section, academic period
    col1, col2, col3 = st.columns(3)
    with col1:
        course = st.text_input("Course", placeholder="Eg: BUS 205")
    with col2:
        section = st.text_input("Section", placeholder="Eg: A")
    with col3:
        academic_period = st.text_input("Academic Period", placeholder="Eg: Spring 2025")

    # Upload CSV files
    st.subheader("Upload Grades Files")
    grade_files = st.file_uploader("Upload the CSV files from the 'Grades' report on Moodle", type=["csv"], accept_multiple_files=True, key="grades")
    
    st.subheader("Upload Questions Files")
    question_files = st.file_uploader("Upload the CSV files from the 'Questions Statistics' report on Moodle", type=["csv"], accept_multiple_files=True, key="questions")
    
    if grade_files and question_files:
        # Group files by their common identifier
        file_pairs = {}
        
        # Process grades files
        for file in grade_files:
            file_name = file.name
            if "-grades.csv" in file_name:
                common_id = file_name.replace("-grades.csv", "")
                file_pairs[common_id] = {"grades": file, "questionstats": None}
        
        # Process questions files
        for file in question_files:
            file_name = file.name
            if "-questionstats.csv" in file_name:
                common_id = file_name.replace("-questionstats.csv", "")
                if common_id not in file_pairs:
                    file_pairs[common_id] = {"grades": None, "questionstats": file}
                else:
                    file_pairs[common_id]["questionstats"] = file

        all_slo_grades = []  # To store processed DataFrames
        
        # Process each pair of files
        for common_id, files in file_pairs.items():
            grades_file = files["grades"]
            questionstats_file = files["questionstats"]
            
            if grades_file and questionstats_file:
                # Save files locally
                grades_file_path = os.path.join(UPLOAD_FOLDER, f"{common_id}-grades.csv")
                questionstats_file_path = os.path.join(UPLOAD_FOLDER, f"{common_id}-questionstats.csv")
                output_file = os.path.join(UPLOAD_FOLDER, f"{common_id}-slo_grades.csv")

                with open(grades_file_path, "wb") as f:
                    f.write(grades_file.getbuffer())
                
                with open(questionstats_file_path, "wb") as f:
                    f.write(questionstats_file.getbuffer())

                try:
                    # Process the uploaded files
                    process_csv(grades_file_path, questionstats_file_path, output_file)
                    st.success(f"Files for {common_id} processed successfully!")
                    
                    # Append the processed DataFrame to the list
                    slo_grades_df = pd.read_csv(output_file)
                    all_slo_grades.append(slo_grades_df)
                    
                except Exception as e:
                    st.error(f"Error occurred with files for {common_id}: {e}")
            else:
                st.warning(f"Skipping {common_id}: Missing grades or questionstats file.")

        if all_slo_grades:
            # Combine all processed DataFrames into one
            combined_slo_grades = pd.concat(all_slo_grades, ignore_index=True)
            
            # Merge rows for the same student
            combined_slo_grades = combined_slo_grades.groupby(["Last name", "First name", "ID number", "Email address"], as_index=False).first()
            
            # Save the combined DataFrame to a new CSV file
            combined_output_path = os.path.join(UPLOAD_FOLDER, "combined_slo_grades.csv")
            combined_slo_grades.to_csv(combined_output_path, index=False)
            
            # Provide a download button for the combined file
            download_file = f"{course.replace(' ', '_')}-{section.replace(' ', '_')}-{academic_period.replace(' ', '_')}_combined.csv"
            with open(combined_output_path, "rb") as f:
                st.download_button("Download Combined SLO Grades", f, file_name=download_file)
            subject = "SLO Grades Report"
            recipient = "recipient@example.com"

            if st.button("Send Email"):
                open_outlook_web_email(subject, recipient)
    else:
        st.warning("Please upload both grades and questions files to proceed.")

if __name__ == "__main__":
    main()