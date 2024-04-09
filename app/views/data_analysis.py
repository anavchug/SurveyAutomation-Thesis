from flask import Blueprint, render_template, request
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from flask import session
from database import get_database_connection

data_analysis_bp = Blueprint('data_analysis', __name__)
mydb = get_database_connection()

@data_analysis_bp.route("/analysis", methods=['GET'])
def home():
    cursor = mydb.cursor()
    company_id = session['user_id']

    # Query to get the prompt ids for a company in session
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
    cursor = mydb.cursor()
    company_id = session['user_id']

    # Fetch data for the specified prompt ID
    survey_query = f"""
    SELECT user.AgeRange, user.Gender, user.Race, user.EmploymentStatus, Survey.responseText
    FROM user
    LEFT JOIN Survey ON user.userId = Survey.UserId
    WHERE Survey.CompanyId = {company_id} AND Survey.PromptId = {prompt_id}
    """
    cursor.execute(survey_query)
    survey_data = cursor.fetchall()

    # Get questions and options
    questions = []
    options = []
    query = f"""
    SELECT Questions.QuestionText, GROUP_CONCAT(questionoptions.optionText SEPARATOR '|') AS options
    FROM Questions
    INNER JOIN questionoptions ON Questions.quesId = questionoptions.quesId
    WHERE Questions.CompanyId = {company_id} AND Questions.PromptId = {prompt_id}
    GROUP BY Questions.QuestionText;
    """
    cursor.execute(query)
    questions_data = cursor.fetchall()
    #print(questions_data)
    for row in questions_data:
        questions.append(row[0])
        options.append(row[1].split('|'))

    # Create plots
    html_plots = []
    for i, question in enumerate(questions):
        question_options = options[i]
        fig = go.Figure()
        for option in question_options:
            option = option.replace(".", "")
            option_counts = {'AgeRange': {}, 'Gender': {}, 'Race': {}, 'EmploymentStatus': {}}
            for row in survey_data:
                response = row[4]
                age_range = row[0]
                gender = row[1]
                race = row[2]
                employment_status = row[3]

                if option in response:
                    print(option)
                    option_counts['AgeRange'][age_range] = option_counts['AgeRange'].get(age_range, 0) + 1
                    option_counts['Gender'][gender] = option_counts['Gender'].get(gender, 0) + 1
                    option_counts['Race'][race] = option_counts['Race'].get(race, 0) + 1
                    option_counts['EmploymentStatus'][employment_status] = option_counts['EmploymentStatus'].get(employment_status, 0) + 1

    
            print(option_counts.items())
            for demographic, demographic_counts in option_counts.items():
                fig.add_trace(go.Bar(
                    x=[demographic + " - " + dem for dem in demographic_counts.keys()],  # Show demographic only on x axis
                    y=list(demographic_counts.values()),
                    name=option + ' - ' + demographic
                ))

        fig.update_layout(
            title=f"{question}",
            xaxis_title="Demographics",
            yaxis_title="Frequency",
            barmode='group'
        )

        html_plot = pio.to_html(fig, full_html=False)
        html_plots.append(html_plot)

    zipped_data = zip(questions, html_plots)

    return render_template('PromptAnalysis.html', prompt_id=prompt_id, zipped_data=zipped_data, questions = questions)


# @data_analysis_bp.route("/analysis/<int:prompt_id>", methods=['GET'])
# def prompt_analysis(prompt_id):
#     cursor = mydb.cursor()
#     company_id = session['user_id']

#     # Fetch data for the specified prompt ID
#     survey_query = f"""
#     SELECT user.AgeRange, user.Gender, user.Race, user.EmploymentStatus, Survey.responseText
#     FROM user
#     LEFT JOIN Survey ON user.userId = Survey.UserId
#     WHERE Survey.CompanyId = {company_id} AND Survey.PromptId = {prompt_id}
#     """
#     cursor.execute(survey_query)
#     survey_data = cursor.fetchall()

#     # Get questions and options
#     questions = []
#     options = []
#     query = f"""
#     SELECT Questions.QuestionText, GROUP_CONCAT(questionoptions.optionText SEPARATOR '|') AS options
#     FROM Questions
#     INNER JOIN questionoptions ON Questions.quesId = questionoptions.quesId
#     WHERE Questions.CompanyId = {company_id} AND Questions.PromptId = {prompt_id}
#     GROUP BY Questions.QuestionText;
#     """
#     cursor.execute(query)
#     questions_data = cursor.fetchall()
#     for row in questions_data:
#         questions.append(row[0])
#         options.append(row[1].split('|'))

#     # Process survey data TODO SOME bug here that is not properly displaying the options for each question, it is only displaying the first option
#     results = []
#     for i, question in enumerate(questions):
#         question_options = options[i]
#         print(options[i])
#         option_counts = {option: {'AgeRange': {}, 'Gender': {}, 'Race': {}, 'EmploymentStatus': {}} for option in question_options}

#         for option in question_options:
#             for row in survey_data:
#                 response = row[4]
#                 age_range = row[0]
#                 gender = row[1]
#                 race = row[2]
#                 employment_status = row[3]

#                 if option in response:
#                     option_counts[option]['AgeRange'][age_range] = option_counts[option]['AgeRange'].get(age_range, 0) + 1
#                     option_counts[option]['Gender'][gender] = option_counts[option]['Gender'].get(gender, 0) + 1
#                     option_counts[option]['Race'][race] = option_counts[option]['Race'].get(race, 0) + 1
#                     option_counts[option]['EmploymentStatus'][employment_status] = option_counts[option]['EmploymentStatus'].get(employment_status, 0) + 1
#                 else:
#                     # Initialize counts to zero if option doesn't exist in response
#                     option_counts[option]['AgeRange'][age_range] = option_counts[option]['AgeRange'].get(age_range, 0)
#                     option_counts[option]['Gender'][gender] = option_counts[option]['Gender'].get(gender, 0)
#                     option_counts[option]['Race'][race] = option_counts[option]['Race'].get(race, 0)
#                     option_counts[option]['EmploymentStatus'][employment_status] = option_counts[option]['EmploymentStatus'].get(employment_status, 0)

#         results.append({'question': question, 'options': option_counts})

#     print(results)

#     # Create plots
#     html_plots = []
#     for result in results:
#         #print(result['question'])
#         for option, counts in result['options'].items():
#             fig = go.Figure()
#             for demographic, demographic_counts in counts.items():
#                 fig.add_trace(go.Bar(
#                     x=[option + " - " + dem for dem in demographic_counts.keys()],  # Combine option and demographic
#                     y=list(demographic_counts.values()),
#                     name=demographic
#                 ))

#             fig.update_layout(
#                 title=f"{result['question']}",  
#                 xaxis_title="Option - Demographic",
#                 yaxis_title="Frequency",
#                 barmode='group'
#             )

#             html_plot = pio.to_html(fig, full_html=False)
#             html_plots.append(html_plot)
#     zipped_data = zip(questions, html_plots)

#     return render_template('PromptAnalysis.html', prompt_id=prompt_id, zipped_data=zipped_data)

   
    # # Query to Get Survey responses for a user for a given company and prompt
    # This query will be used to do a demographic analysis

    # survey_query = f"""
    # SELECT user.userId, user.AgeRange, user.Gender,user.Race, user.EmploymentStatus,
    #        Survey.CompanyId, Survey.PromptId, questions.quesId, questions.QuestionText,
    #        Survey.responseText
    # FROM user
    # LEFT JOIN Survey ON user.userId = Survey.UserId
    # LEFT JOIN questions ON Survey.quesId = questions.quesId
    # WHERE Survey.CompanyId = {company_id }AND Survey.PromptId = {prompt_id}
    # GROUP BY user.userId, user.AgeRange, user.Gender,
    #          user.Race, user.EmploymentStatus, Survey.CompanyId, 
    #          Survey.PromptId, questions.quesId, questions.QuestionText, Survey.responseText;
    # """
    # cursor.execute(survey_query)
    # survey_results = cursor.fetchall()
    # print(survey_results)

    # cursor.close()

# # Prepare data for demographic analysis
#     demographic_data = {'AgeRange': [], 'Gender': [], 'Race': [], 'EmploymentStatus': []}
#     for row in survey_results:
#        # print(row[4])
#         responses = row[9]  # Split responses for each user
#         demographic_data['AgeRange'].extend([row[1]] )
#         demographic_data['Gender'].extend([row[2]] )
#         demographic_data['Race'].extend([row[3]] )
#         demographic_data['EmploymentStatus'].extend([row[4]])

#     # Convert data to DataFrame
#     df_demographic = pd.DataFrame(demographic_data)
#    # print(df_demographic)

#     # Create demographic analysis visualizations
#     figs = []

#     # for question in result:
#     #         # Count occurrences of responses for the current question
#     #         response_counts = df_demographic.apply(lambda x: x.value_counts()).T

#     #         # Create a bar chart for the current question
#     #         fig = go.Figure()
#     #         for col in response_counts.columns:
#     #             fig.add_trace(go.Bar(x=response_counts.index, y=response_counts[col], name=col))

#     #         fig.update_layout(title=f'"{question["question"]}"',
#     #                         xaxis_title='Response',
#     #                         yaxis_title='Frequency',
#     #                         barmode='group')

#     #         figs.append(fig)

#     return render_template('PromptAnalysis.html', prompt_id=prompt_id, questions=result, plots=figs)


# Query to Get Survey responses for a user for a given company and prompt

# SELECT user.userId, user.AgeRange, user.Gender,user.Race, user.EmploymentStatus,
#        Survey.CompanyId, Survey.PromptId, questions.quesId, questions.QuestionText,
#        Survey.responseText
# FROM user
# LEFT JOIN Survey ON user.userId = Survey.UserId
# LEFT JOIN questions ON Survey.quesId = questions.quesId
# WHERE Survey.CompanyId = 1 AND Survey.PromptId = 1
# GROUP BY user.userId, user.AgeRange, user.Gender,
#          user.Race, user.EmploymentStatus, Survey.CompanyId, 
#          Survey.PromptId, questions.quesId, questions.QuestionText, Survey.responseText;




#  SELECT user.userId, user.AgeRange, user.Gender,user.Race, user.EmploymentStatus,Survey.CompanyId, Survey.PromptId,  
#         GROUP_CONCAT(Survey.responseText SEPARATOR '|') AS AllResponses
#         FROM user
#         LEFT JOIN Survey ON user.userId = Survey.UserId
#         WHERE Survey.CompanyId = {company_id} AND Survey.PromptId = {prompt_id}
#         GROUP BY user.userId, user.AgeRange, user.Gender,user.Race, user.EmploymentStatus,Survey.CompanyId, Survey.PromptId;





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
