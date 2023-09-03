from flask import Blueprint, render_template
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
    cursor.execute(
    "SELECT * FROM Survey INNER JOIN User ON Survey.UserId = User.userId")
    data = cursor.fetchall()
    cursor.close()

    # Convert data to DataFrame
    column_names = ["SurveyID", "CompanyId", "UserId", "QuesId", "PromptId", "response1", "response2", "response3", "response4", "response5",
    "response6", "response7", "response8", "response9",  "response10", "userId", "FirstName","LastName", "Email", "AgeRange", "Gender", "Race", "EmploymentStatus",]

    data = pd.DataFrame(data, columns=column_names)

    # For now, I am using CompanyId here, this should display all the questions for that company. We ideally want it to be PromptId
    # Extract the response columns
    responses = data[
        [ "CompanyId","response1","response2", "response3","response4", "response5", "response6", "response7","response8", "response9","response10", ]
    ]

    # extract the demographic columns
    demographics = data[["AgeRange", "Gender", "Race", "EmploymentStatus"]]
    print(demographics)
    # Get the company ID from the session
    company_id = session['user_id']
    print("Company ID IS- ", company_id)
    
    # Retrieve questions from the Questions table
    cursor = mydb.cursor()
    # Fetching questions that belong to the company in session
    query = f"""
        SELECT QuesId, CompanyId, Question1, Question2, Question3, Question4, 
            Question5, Question6, Question7, Question8, Question9, Question10 
        FROM Questions
        WHERE CompanyId = {company_id}
    """
    cursor.execute(query)
    questions_data = cursor.fetchall()
    print(questions_data)
    cursor.close()

    # Create a dictionary to map question IDs to question texts
    question_mapping = {
        row[0]: [q for q in row[2:] if q is not None] for row in questions_data
    }
    print("Question Mapping" , question_mapping)   # ----------Code is correct till here------------------

    # Check if there are responses and questions
    if responses.empty or not question_mapping:
        # There are no responses or questions for this company
        return render_template("nosurveys.html")
    
    # Create a bar chart for each response column  (This should be only for that company and not all the response columns)
    charts = []
    question_texts = []  # List to store question texts
    index = 0
    i = 1

    # Assuming companyId is obtained from the session
    companyId = session['user_id']
    # promptId =  session.get('promptId')
    # print("Prompt ID ISSS- ", promptId)
    # Filter the responses DataFrame for the current company
    responses_for_company = responses[responses['CompanyId'] == companyId]
    print("Responses for Company", responses_for_company)

    for column in responses_for_company.columns[1:]:
    # Filter out empty responses
        non_empty_responses = responses_for_company[column].dropna()

        # Proceed only if there are non-empty responses
        if not non_empty_responses.empty:
            # question_id = int( column[8:] ) 
            question_id = companyId         # this should be promptId coz a promptId and questionId will always be the same
            print("Question ID: ", question_id)
            # Extract the question ID from the column name
            question_texts.extend(question_mapping.get(question_id, []))
            print("Question Texts", question_texts)

            chart = px.bar(
                non_empty_responses.value_counts(),
                x=non_empty_responses.unique(),
                y=non_empty_responses.value_counts(),
            )
            chart.update_layout(
                title_text=f"Question {str(i)} : {question_texts[index]}",
                xaxis_title="Responses",
                yaxis_title="Count",
            )
            charts.append(chart)
            index = index + 1
            i = i + 1

    # Convert the Plotly figures to JSON
    graphJSONs = [chart.to_json() for chart in charts]

    return render_template(
        "AnalysisDashboard.html",
        graphJSONs=graphJSONs,
        num_charts=len(charts),
        question_mapping=question_mapping,
        question_texts=question_texts,
    )
# Fix this as well for the responses
@data_analysis_bp.route("/demographics/<int:question_id>")
def demographics(question_id):
    companyId = session.get('user_id')

    # Check if companyId is available in the session
    if companyId is not None:
        mydb = get_database_connection()
        cursor_age = mydb.cursor()
        age_query = """
        SELECT
            U.AgeRange,
            S.{response_column},
            COUNT(*) AS Frequency
        FROM
            User U
            JOIN Survey S ON U.userId = S.UserId
            JOIN Questions Q ON Q.CompanyId = S.CompanyId
        WHERE
            S.CompanyId = Q.CompanyId
            AND Q.Question{question_id} IS NOT NULL
            AND S.CompanyId = %s
        GROUP BY
            U.AgeRange,
            S.{response_column}
        """

        cursor_age.execute(age_query.format(question_id=question_id, response_column=f"response{question_id}"), (companyId,))
        data_age = cursor_age.fetchall()
        cursor_age.close()

        cursor_gender = mydb.cursor()
        gender_query = """
        SELECT
            U.Gender,
            S.{response_column},
            COUNT(*) AS Frequency
        FROM
            User U
            JOIN Survey S ON U.userId = S.UserId
            JOIN Questions Q ON Q.CompanyId = S.CompanyId
        WHERE
            S.CompanyId = Q.CompanyId
            AND Q.Question{question_id} IS NOT NULL
            AND S.CompanyId = %s
        GROUP BY
            U.Gender,
            S.{response_column}
        """

        cursor_gender.execute(gender_query.format(question_id=question_id, response_column=f"response{question_id}"), (companyId,))
        data_gender = cursor_gender.fetchall()
        cursor_gender.close()

    cursor_race = mydb.cursor()
    race_query = """
    SELECT
        U.Race,
        S.{response_column},
        COUNT(*) AS Frequency
    FROM
        User U
        JOIN Survey S ON U.userId = S.UserId
        JOIN Questions Q ON Q.CompanyId = S.CompanyId
    WHERE
        S.CompanyId = Q.CompanyId
        AND Q.Question{question_id} IS NOT NULL
        AND S.CompanyId = %s
    GROUP BY
        U.Race,
        S.{response_column}
    """

    cursor_race.execute(race_query.format(question_id=question_id, response_column=f"response{question_id}"), (companyId,))
    data_race= cursor_race.fetchall()
    cursor_race.close()

    cursor_employment = mydb.cursor()
    employmentStatus_query = """
    SELECT
        U.EmploymentStatus,
        S.{response_column},
        COUNT(*) AS Frequency
    FROM
        User U
        JOIN Survey S ON U.userId = S.UserId
        JOIN Questions Q ON Q.CompanyId = S.CompanyId
    WHERE
        S.CompanyId = Q.CompanyId
        AND Q.Question{question_id} IS NOT NULL
        AND S.CompanyId = %s
    GROUP BY
        U.EmploymentStatus,
        S.{response_column}
    """
    cursor_employment.execute(employmentStatus_query.format(question_id=question_id, response_column=f"response{question_id}"), (companyId,))
    data_employment= cursor_employment.fetchall()
    cursor_employment.close()

    # Creating columns for different demographics for the Data Frame
    column_names_for_age = ["AgeRange", "Response", "Frequency"]
    column_names_for_gender = ["Gender", "Response", "Frequency"]
    column_names_for_race = ["Race", "Response", "Frequency"]
    column_names_for_employment_status = ["EmploymentStatus", "Response", "Frequency"]


    #Convert demographics to Dataframe
    age_data = pd.DataFrame(data_age, columns=column_names_for_age)
    gender_data = pd.DataFrame(data_gender, columns=column_names_for_gender)
    race_data = pd.DataFrame(data_race, columns=column_names_for_race)
    employmentStatus_data = pd.DataFrame(data_employment, columns=column_names_for_employment_status)

    # Creating Charts for each demographic
    age_chart = px.bar(age_data, x="AgeRange", y="Frequency", color="Response", barmode="group")
    gender_chart = px.bar(gender_data, x="Gender", y="Frequency", color="Response", barmode="group")
    race_chart = px.bar(race_data, x="Race", y="Frequency", color="Response", barmode="group")
    employmentStatus_chart = px.bar(employmentStatus_data, x="EmploymentStatus", y="Frequency", color="Response", barmode="group")

    # Converting charts to Json
    age_graphJSON = age_chart.to_json()
    gender_graphJSON = gender_chart.to_json()
    race_graphJSON = race_chart.to_json()
    employmentStatus_graphJSON = employmentStatus_chart.to_json()

    return render_template("demographics.html", age_graphJSON=age_graphJSON, 
                        gender_graphJSON = gender_graphJSON, race_graphJSON = race_graphJSON, 
                        employmentStatus_graphJSON = employmentStatus_graphJSON  )
