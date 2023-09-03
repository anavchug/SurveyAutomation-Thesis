from flask import Flask, Blueprint, redirect, request, render_template, url_for, session
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

model_engine = "text-davinci-002"

# Connect to MySQL database
mydb = get_database_connection()
cursor = mydb.cursor()

generated_questions = []
formatted_questions = []
formatted_answers = []
emails = ["aakarshachugh23@gmail.com", "aakarshachugh19@gmail.com"]

@company_bp.route("/company", methods=["GET", "POST"])
def company():
    if request.method == "POST":
        name = request.form["name"]
        branch = request.form["branch"]
        email = request.form["email"]
        phone = request.form["phone"]
        prompt = request.form["prompt"]

        # Check if the company already exists in the database
        mydb = get_database_connection()
        cursor = mydb.cursor()

        query = "SELECT companyId FROM companies WHERE name = %s AND branch = %s"
        values = (name, branch)
        cursor.execute(query, values)
        existing_company = cursor.fetchone()

        if existing_company:
            companyId = existing_company[0]  # Retrieve the existing companyId
        else:
            # Generate initial questions using the generate_question method
            generated_questions = generate_question(prompt)
            formatted_questions.clear()
            formatted_answers.clear()
            format_generated_questions(generated_questions, formatted_questions, formatted_answers)

            # Store the formatted questions and answers in the session
            session["formatted_questions"] = formatted_questions
            session["formatted_answers"] = formatted_answers
            session["prompt"] = prompt

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

        return redirect(url_for("company.survey_questions"))
    else:
        return render_template("Company Interface.html")

@company_bp.route("/survey_questions", methods=["GET", "POST"])
def survey_questions():
    global formatted_questions, formatted_answers

    # Generate the survey questions based on the prompt and display it on the page
    if request.method == "POST" and "generate_questions" in request.form:
       
       # Get the prompt of the company that is in session
        companyId = session['user_id']
        sql = "SELECT prompt FROM company_prompts WHERE companyId = %s"
        cursor.execute(sql, (companyId,))
        result = cursor.fetchone()
        prompt = result[0] if result else None

        if prompt is None:
            return "Error: No prompt found in the company_prompts table."
        
        # Generate additional questions using the generate_question method
        additional_questions = []
        additional_questions = generate_question(prompt)
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
        # Get the number of questions
        num_questions = len(formatted_questions)

        # Create a list with 10 elements, where the first element is the companyId
        values = [companyId]
        # Append the questions to the values list
        values.extend(formatted_questions)

        # Pad the values list with None for remaining columns
        values += [None] * (10 - num_questions)
        # Build the SQL query
        sql = "INSERT INTO Questions (companyId, question1, question2, question3, question4, question5, question6, question7, question8, question9, question10) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        # Execute the SQL query
        cursor.execute(sql, values)
        mydb.commit()

        return redirect( url_for("company.finalize_questions",question_data=zip(formatted_questions, formatted_answers),))
    
    # Retrieve the formatted questions and answers from the session
    formatted_questions = session.get("formatted_questions", [])
    formatted_answers = session.get("formatted_answers", [])
    return render_template("SurveyQuestions.html", question_data= zip(formatted_questions, formatted_answers))

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

@company_bp.route("/finalize_questions", methods=["GET", "POST"])
def finalize_questions():
    current_route = "/finalize_questions"

    if request.method == "POST":
        companyId = session['user_id']
        print("Company Id: " , companyId)
        send_survey_invitations(emails, companyId)
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

        # CompanyId, QuesId and promptId for any given survey are the same
        quesId = companyId 
        promptId = companyId

        # Insert data into the database
        sql = "INSERT INTO User (firstname, lastname, email, agerange, gender, race, employmentstatus) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (firstname, lastname, email, agerange, gender, race, employmentstatus)
        cursor.execute(sql, values)
        mydb.commit()

        # getting the user id of the last inserted row
        userId = cursor.lastrowid

        # Generate the SQL query
        survey_sql = "INSERT INTO Survey (CompanyId, UserId, QuesId, PromptId, response1, response2, response3, response4, response5, response6, response7, response8, response9, response10)VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        # Prepare the values for the SQL query
        survey_values = [
            companyId,
            userId,  # Use the corresponding user ID from the User table
            quesId,  # Use the corresponding question ID
            promptId,  # Use the corresponding prompt ID
        ]
        form_data = request.form
        # Retrieve and append the responses to the values list
        user_data_keys = [ "firstname", "lastname",  "email", "agerange", "gender","race", "employmentstatus", ]
        for key, value in form_data.items():
            if key not in user_data_keys:
                survey_values.append(value)

        survey_values += [None] * (14 - len(survey_values))
        print(len(survey_values))

        cursor.execute(survey_sql, survey_values)
        mydb.commit()

        # Return success message-
        return "Your responses have been recorded"

    # Render the GeneratedQuestions.html page
    else:
        # Retrieve the token and email from the query parameters
        token = request.args.get("token")
        email = request.args.get("email")
        companyId = request.args.get("companyId")
        current_route = "/survey"

        print("COMPANY ID: " , companyId)
        print("EMAIL", email)
        print("Token", token)
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

def generate_question(prompt):
    try:
        completions = openai.Completion.create(
            engine=model_engine,
            prompt="Please generate a distinct multiple-choice question for a user survey, with 4 options labeled 'a)', 'b)', 'c)', and 'd)'. The question should be based on the given prompt, but should not mention the name of the product unless specified. Additionally, please ensure that no generated question is repeated in any completion."
            + prompt,
            max_tokens=1024,
            n=2,
            stop=None,
            temperature=0.85,
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

