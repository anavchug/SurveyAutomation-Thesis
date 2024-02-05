from flask import Blueprint, render_template, request
import pandas as pd
import plotly.express as px
from flask import session
from database import get_database_connection

data_analysis_bp = Blueprint('data_analysis', __name__)

@data_analysis_bp.route("/analysis", methods=['GET'])
def home():
    # Fetch data from the MySQL database
    mydb = get_database_connection()
    cursor = mydb.cursor()
    # cursor.execute(
    #     "SELECT * FROM Survey INNER JOIN User ON Survey.UserId = User.userId")
    
    query = f"""Select Questions.quesId, Questions.CompanyId, Questions.PromptId, 
    Questions.QuestionText, questionoptions.optionText
    FROM Questions
    INNER JOIN questionoptions
    ON Questions.quesId = questionoptions.quesId
    """
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()

    # # Convert data to DataFrame
    # column_names = ["SurveyID", "UserId", "responseText", "userId", "FirstName", "LastName", "Email", "AgeRange", "Gender", "Race", "EmploymentStatus"]

    # data = pd.DataFrame(data, columns=column_names)
    # print("Data", data)

    
    for row in data:
        question = row[3]
        print(row[3] + " " + row[4])
    
    # question_mapping = {
    #     row[3]: row[4] for row in data
    # }
    # print("Question Mapping", question_mapping)


    #return data
    #return question_mapping

    # Get the company ID from the session
    company_id = session['user_id']

    # Retrieve questions from the Questions table
    cursor = mydb.cursor()
    # Fetching questions that belong to the company in session
    # query = f"""
    #     SELECT QuesId, CompanyId, QuestionText
    #     FROM Questions
    #     WHERE CompanyId = {company_id}
    # """

    # query to select questions and its options for the company in session. Need to filter the data further based on prompts
    query = f"""
    SELECT Questions.QuestionText, GROUP_CONCAT(questionoptions.optionText) AS options
    FROM Questions
    INNER JOIN questionoptions ON Questions.quesId = questionoptions.quesId
    WHERE Questions.CompanyId = {company_id}
    GROUP BY Questions.QuestionText;
    """
    cursor.execute(query)
    questions_data = cursor.fetchall()
    print("Question Data", questions_data)
    cursor.close()

     # Structure the data into a list of dictionaries
    result = []
    for row in questions_data:
        question = row[0]
        options = row[1].split(',')  # Split options string into a list
        result.append({'question': question, 'options': options})

    return render_template('AnalysisDashboard.html', questions=result)

    # Create a dictionary to map question IDs to question texts
    # question_mapping = {
    #     row[0]: row[2] for row in questions_data
    # }
    # print("Question Mapping", question_mapping)

    return questions_data

    # # Check if there are responses and questions
    # if data.empty or not question_mapping:
    #     # There are no responses or questions for this company
    #     return render_template("nosurveys.html")

    # # Create charts for responses
    # charts = []

    # for question_id, question_text in question_mapping.items():
    #     # Filter responses for the current question
    #     print(f"Question ID: {question_id}, Question Text: {question_text}")
    #     responses_column = f"responseText_{question_id}"
    #     responses = data[data['UserId'] == company_id]['responseText'].dropna()
    #     print(responses)

    #     if not responses.empty:
    #         # Create a bar chart for responses
    #         chart = px.bar(
    #             responses.value_counts().reset_index(),
    #             x='responseText',  # Change 'index' to 'responseText'
    #             y='count',  # Use 'count' as the y-axis
    #             labels={'responseText': 'Response', 'count': 'Count'},
    #             title=f"Question: {question_text}",
    #         )
    #         charts.append(chart)

    # # Convert the Plotly figures to JSON
    # graphJSONs = [chart.to_json() for chart in charts]

    # return render_template(
    #     "AnalysisDashboard.html",
    #     graphJSONs=graphJSONs,
    #     num_charts=len(charts),
    # )
