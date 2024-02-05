from flask import Flask, Blueprint, g, redirect, request, render_template, url_for, session
from jinja2 import Environment
import openai
import re
import pandas as pd
from database import get_database_connection
from emailInvitations import send_survey_invitations

company_bp = Blueprint("company", __name__)

def get_type(value):
    return type(value).__name__

env = Environment()
env.filters['type'] = get_type

# Apply for an OpenAI API key and paste it here
openai.api_key = "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"

# model_engine = "text-davinci-002"
model_engine = "gpt-3.5-turbo-instruct"

# Connect to MySQL database
mydb = get_database_connection()
cursor = mydb.cursor()

generated_questions = []
formatted_questions = []
formatted_answers = []
emails = ["aakarshachugh23@gmail.com", "aakarshachugh19@gmail.com"]
# global_prompt = None

@company_bp.route("/company", methods=["GET", "POST"])
def company():
    # Check if the company already exists in the database
    mydb = get_database_connection()
    cursor = mydb.cursor()
    # Get the company name from the session
    company_id_in_session = session.get('user_id')
    global global_prompt

    query = "SELECT companyId FROM companies WHERE companyId = %s"
    values = (company_id_in_session,)  # Use the company id from the session
    cursor.execute(query, values)
    existing_company = cursor.fetchone()

    if request.method == "POST":
        prompt = request.form["prompt"]
        global_prompt = prompt
        #if the company exists in the database then add the prompt to that company's company_prompt table and generate questions
        if existing_company:
            companyId = existing_company[0]  # Use the existing companyId
            # Insert the prompt into the company_prompts table with the corresponding companyId value
            promptQuery = "INSERT INTO company_prompts (companyId, prompt) VALUES (%s, %s)"
            values = (companyId, prompt)
            cursor.execute(promptQuery, values)
            mydb.commit()
        
        #else this is a new company
        else:
            name = request.form["name"]
            branch = request.form["branch"]
            email = request.form["email"]
            phone = request.form["phone"]

            # # Generate initial questions using the generate_question method
            # generated_questions = generate_question(prompt)
            # formatted_questions.clear()
            # formatted_answers.clear()
            # format_generated_questions(generated_questions, formatted_questions, formatted_answers)

            # # Store the formatted questions and answers in the session
            # session["formatted_questions"] = formatted_questions
            # session["formatted_answers"] = formatted_answers
            # session["prompt"] = prompt

            # Insert company data into the database
            sql = "INSERT INTO companies (name, branch, email, phone, userId) VALUES (%s, %s, %s, %s, %s)"
            values = (name, branch, email, phone, session['user_id'])  # Use the user ID from the session
            cursor.execute(sql, values)
            mydb.commit()

            # Retrieve the companyId of the inserted row
            companyId = session['user_id']

            # Insert the prompt into the company_prompts table with the corresponding companyId value
            promptQuery = "INSERT INTO company_prompts (companyId, prompt) VALUES (%s, %s)"
            values = (companyId, prompt)
            cursor.execute(promptQuery, values)
            mydb.commit()

        # Generate initial questions using the generate_question method
        generated_questions = generate_question(prompt)
        formatted_questions.clear()
        formatted_answers.clear()
        format_generated_questions(generated_questions, formatted_questions, formatted_answers)

        # Store the formatted questions and answers in the session
        session["formatted_questions"] = formatted_questions
        session["formatted_answers"] = formatted_answers
        session["prompt"] = prompt

        return redirect(url_for("company.survey_questions"))
    
    #else it was a GET request
    else:
        return render_template("Company Interface.html", existing_company=existing_company)

@company_bp.route("/survey_questions", methods=["GET", "POST"])
def survey_questions():
    global formatted_questions, formatted_answers
    global global_prompt

    # Generate the survey questions based on the prompt and display them on the page
    if request.method == "POST" and "generate_questions" in request.form:
        # Get the prompt of the company that is in session
        # companyId = session['user_id']
        # sql = "SELECT prompt FROM company_prompts WHERE companyId = %s"
        # cursor.execute(sql, (companyId,))
        # result = cursor.fetchone()
        # prompt = result[0] if result else None

        # if prompt is None:
        #     return "Error: No prompt found in the company_prompts table."

        # Generate additional questions using the generate_question method
        additional_questions = generate_question(global_prompt)
        formatted_additional_questions = []
        formatted_additional_answers = []
        format_generated_questions(additional_questions, formatted_additional_questions, formatted_additional_answers)

        # Append the additional questions and answers to the existing lists
        formatted_questions.extend(formatted_additional_questions)
        formatted_answers.extend(formatted_additional_answers)

        # Store the updated formatted questions and answers in the session
        session["formatted_questions"] = formatted_questions
        session["formatted_answers"] = formatted_answers

        return redirect(url_for("company.survey_questions"))

    elif request.method == "POST":
        # Retrieve the stored questions and answers from the session
        formatted_questions = session.get("formatted_questions", [])
        formatted_answers = session.get("formatted_answers", [])

        print("Final Questions", formatted_questions)
        print("Final Answers", formatted_answers)

        companyId = session['user_id']

        # Insert the questions into the Questions table
        insert_questions(companyId, global_prompt, formatted_questions)

        # Now, insert the options for each question into the QuestionOptions table
        quesIds = retrieve_question_ids(companyId)
        insert_question_options(quesIds, formatted_answers)

        return redirect(url_for("company.finalize_questions"))

    # Retrieve the formatted questions and answers from the session
    formatted_questions = session.get("formatted_questions", [])
    formatted_answers = session.get("formatted_answers", [])
    return render_template("SurveyQuestions.html", question_data=zip(formatted_questions, formatted_answers))


@company_bp.route("/finalize_questions", methods=["GET", "POST"])
def finalize_questions():
    current_route = "/finalize_questions"

    if request.method == "POST":
        companyId = session['user_id']
        print("Company Id: " , companyId)
        # I want to somehow send the prompt encoded as well. Use same strategy here to search the prompt based on company id and global prompt and send the
        # promptId as a parameter, then on the user end, get that id and put it in the Survey table 
        # Fetch the PromptId based on companyId and prompt
        prompt_sql = "SELECT promptId FROM company_prompts WHERE companyId = %s AND prompt = %s"
        prompt_values = (companyId, global_prompt)
        cursor.execute(prompt_sql, prompt_values)
        prompt_result = cursor.fetchone()

        if prompt_result:
            # If a matching prompt is found, use its PromptId
            promptId = prompt_result[0]

        send_survey_invitations(emails, companyId, promptId)
        return "Survey has been sent to your email list"
   
    # Render the generated questions page
    return render_template(
        "GeneratedQuestions.html",
        question_data=zip(formatted_questions, formatted_answers),
        current_route=current_route,
    )

@company_bp.route("/survey", methods=["GET", "POST"])
def survey():
    answers = request.form
    global companyId, email, token
    
    if request.method == "POST":
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        email = request.form["email"]
        agerange = request.form["agerange"]
        gender = request.form["gender"]
        race = request.form["race"]
        employmentstatus = request.form["employmentstatus"]

        company_id = session.get('companyId')
        prompt_id = session.get('promptId')

        print(request.args)
        print("Company Id in Survey form", company_id)
        print("Prompt Id in Survey form", prompt_id)

        #companyId = session['user_id']
        # quesIds = retrieve_question_ids(companyId)

        # Insert user data into the User table
        user_id = insert_user_data(firstname, lastname, email, agerange, gender, race, employmentstatus)

        # Insert survey responses into the Survey table
        insert_survey_responses(user_id, answers, company_id, prompt_id)

        # Return success message
        return "Your responses have been recorded"

    # Render the GeneratedQuestions.html page
    else:
        # Retrieve the token and email from the query parameters
        token = request.args.get("token")
        email = request.args.get("email")
        
        companyId = request.args.get("companyId")
        prompt_id = request.args.get("promptId")

        # Store in the session for use in the POST request
        session['companyId'] = companyId
        session['promptId'] = prompt_id
        
        # print("Email", email)
        # print("Company ID in Survey form", companyId)
        # print("Prompt ID in Survey form", prompt_id) 
        current_route = "/survey"

        # Retrieve the formatted questions and answers from the session
        formatted_questions = session.get("formatted_questions", [])
        formatted_answers = session.get("formatted_answers", [])
        return render_template(
            "GeneratedQuestions.html",
            token=token,
            email=email,
            question_data=zip(formatted_questions, formatted_answers),
            current_route=current_route,
        )
def insert_questions(companyId, global_prompt, formatted_questions): 
    for question in formatted_questions:
        # Fetch the PromptId based on companyId and prompt
        prompt_sql = "SELECT promptId FROM company_prompts WHERE companyId = %s AND prompt = %s"
        prompt_values = (companyId, global_prompt)
        cursor.execute(prompt_sql, prompt_values)
        prompt_result = cursor.fetchone()

        if prompt_result:
            # If a matching prompt is found, use its PromptId
            promptId = prompt_result[0]

            # Build the SQL query for inserting questions
            sql = "INSERT INTO Questions (CompanyId, PromptId, QuestionText) VALUES (%s, %s, %s)"
            values = (companyId, promptId, question)
            cursor.execute(sql, values)
            mydb.commit()
        else:
            print(f"Error: No matching prompt found for company {companyId} and question {question}")


def insert_question_options(quesId, formatted_answers):
    # Insert options for each question into the QuestionOptions table
    companyId = session['user_id']
    # Fetch the PromptId based on companyId and prompt
    prompt_sql = "SELECT promptId FROM company_prompts WHERE companyId = %s AND prompt = %s"
    prompt_values = (companyId, global_prompt)
    cursor.execute(prompt_sql, prompt_values)
    prompt_result = cursor.fetchone()

    if prompt_result:
        # If a matching prompt is found, use its PromptId
        promptId = prompt_result[0]

    for i, options in enumerate(formatted_answers):
        for j, option in enumerate(options):
            option_number = chr(ord('a') + j)  # Convert 0-based index to 'a', 'b', 'c', 'd'
            option_text = option.strip()
            print(option_number)
            print(option_text)
            # Build the SQL query for inserting options
            sql = "INSERT INTO QuestionOptions (CompanyId, PromptId, quesId, optionText) VALUES (%s, %s, %s, %s)"
            # values = (companyId, companyId, quesId[i], option_number + ') ' + option_text)
            values = (companyId, promptId, quesId[i], option_text)
            cursor.execute(sql, values)
    
    mydb.commit()

def retrieve_question_ids(companyId):
    # Retrieve the question IDs for the inserted questions

    # sql = "SELECT quesId FROM Questions WHERE CompanyId = %s"
    sql = f"""
    SELECT Questions.quesId
    FROM Questions
    INNER JOIN company_prompts ON Questions.PromptId = company_prompts.promptId
    INNER JOIN companies ON Questions.CompanyId = companies.companyId
    WHERE companies.CompanyId = %s AND company_prompts.prompt = %s
"""
    cursor.execute(sql, (companyId, global_prompt) )
    result = cursor.fetchall()
    quesIds = [row[0] for row in result]
    return quesIds

@company_bp.route("/delete_question/<int:question_index>", methods=["POST"])
def delete_question(question_index):
    global formatted_questions, formatted_answers

    print("Index is ", question_index - 1)
    # Delete the question and corresponding answer from the formatted lists
    formatted_questions.pop(question_index - 1)
    formatted_answers.pop(question_index - 1)

    # Update the session data
    session["formatted_questions"] = formatted_questions
    session["formatted_answers"] = formatted_answers

    return redirect(url_for("company.survey_questions"))

def insert_user_data(firstname, lastname, email, agerange, gender, race, employmentstatus):
    # Insert user data into the User table
    sql = "INSERT INTO User (FirstName, LastName, Email, AgeRange, Gender, Race, EmploymentStatus) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    values = (firstname, lastname, email, agerange, gender, race, employmentstatus)
    cursor.execute(sql, values)
    mydb.commit()
    return cursor.lastrowid

def insert_survey_responses(userId, answers, company_id, prompt_id):
    # Insert survey responses into the Survey table
    sql = "INSERT INTO Survey (UserId, CompanyId, PromptId, ResponseText) VALUES (%s, %s, %s, %s)"

    questions_started = False  # Flag to track when the questions start

    # answers contains all the user responses but we want to only add the responses of questions after the demographic info that ends at emp status
    for key, response in answers.items():
        if key == "employmentstatus":
            questions_started = True  # Set the flag to True when employmentstatus is encountered
        elif questions_started:
            values = (userId, company_id, prompt_id, response)
            cursor.execute(sql, values)

    mydb.commit()


def generate_question(prompt):
    try:
        completions = openai.Completion.create(
            engine=model_engine,
            prompt="Please generate a distinct multiple-choice question for a user survey, with 4 options labeled 'a)', 'b)', 'c)', and 'd)'. The question should be based on the given prompt, but should not mention the name of the product unless specified. Additionally, please ensure that no generated question is repeated in any completion."
            + prompt,
            max_tokens=1024,
            n=2,
            stop=None,
            temperature=0.7,
        )
        # Define an empty list to store the generated questions
        questions = []
        # Loop through the generated questions
        for choice in completions.choices:
            # Store the text of the generated question
            question = choice.text.strip()

            # Add the generated question to the list of questions
            questions.append(question)

        # Update the list of previously generated questions with the new questions
        generated_questions.extend(questions)

        # Return the list of generated questions
        return questions
    except Exception as e:
        print("An error occurred:", str(e))

def format_generated_questions(generated_questions, formatted_question_list, formatted_answer_list):
    try:
        for question in generated_questions:
            # Extract the question text using a regular expression
            question_match = re.match(r"(.*\?)", question)
            if question_match:
                formatted_question_list.append(question_match.group(1).strip())

            # Extract the options and format them to remove extra spaces
            options = re.split(r'[a-d]\)', question.split("?")[1].strip())
            print("Options", options)
            if options:
                formatted_answers_list = [option for option in options if option]
                formatted_answer_list.append(formatted_answers_list)
    except Exception as e:
        print("An error occurred:", str(e))

