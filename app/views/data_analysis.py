from flask import Blueprint, render_template, request
import pandas as pd
import plotly.express as px
from flask import session
from database import get_database_connection

data_analysis_bp = Blueprint('data_analysis', __name__)
mydb = get_database_connection()

@data_analysis_bp.route("/analysis", methods=['GET'])
def home():
    # Fetch data from the MySQL database
    cursor = mydb.cursor()

    # Get the company ID from the session
    company_id = session['user_id']

    getNumberOfPrompts = f"""
    SELECT COUNT(PromptId) as NoOfPrompts
    FROM company_prompts
    WHERE companyId = {company_id};
    """
    cursor.execute(getNumberOfPrompts)
    numPrompts = cursor.fetchone()[0]

    getPromptIds = f"""
    SELECT promptId FROM company_prompts
    WHERE companyId = {company_id};
    """
    cursor.execute(getPromptIds)
    prompt_ids = cursor.fetchall()

    cursor.close()

    return render_template('AnalysisDashboard.html', prompt_ids=prompt_ids)

@data_analysis_bp.route("/analysis/<int:prompt_id>", methods=['GET'])
def prompt_analysis(prompt_id):
    # Fetch data from the MySQL database
    cursor = mydb.cursor()

    # Get the company ID from the session
    company_id = session['user_id']

    # Fetch data for the specified prompt ID
    query = f"""
    SELECT Questions.QuestionText, GROUP_CONCAT(questionoptions.optionText SEPARATOR '|') AS options
    FROM Questions
    INNER JOIN questionoptions ON Questions.quesId = questionoptions.quesId
    WHERE Questions.CompanyId = {company_id} AND Questions.PromptId = {prompt_id}
    GROUP BY Questions.QuestionText;
    """
    cursor.execute(query)
    questions_data = cursor.fetchall()

    # Structure the data into a list of dictionaries
    result = []
    for row in questions_data:
        question = row[0]
        options = row[1].split('|')  # Split options string into a list
        result.append({'question': question, 'options': options})

    cursor.close()

    return render_template('PromptAnalysis.html', prompt_id=prompt_id, questions=result)


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
