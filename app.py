import streamlit as st
import pandas as pd
import os

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

    slo_response_columns = [f"Q. {int(q)} /" for q in slo_question_numbers]
    slo_response_columns = [col for col in grades_df.columns if any(col.startswith(f"Q. {int(q)}") for q in slo_question_numbers)]
    
    slo_grades_df = grades_df[["Last name", "First name", "ID number", "Email address"] + slo_response_columns]
    slo_grades_df.to_csv(output_path, index=False)

def main():
    st.title("SLO Grades Processing")

    st.write("Upload the two CSV files (grades and questions) for processing.")

    # Upload CSV files
    file1 = st.file_uploader("Upload Grades CSV", type=["csv"])
    file2 = st.file_uploader("Upload Questions CSV", type=["csv"])

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
            
            # Provide download link for processed file
            with open(OUTPUT_FILE, "rb") as f:
                st.download_button("Download SLO Grades", f, file_name=OUTPUT_FILE)
        
        except Exception as e:
            st.error(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
