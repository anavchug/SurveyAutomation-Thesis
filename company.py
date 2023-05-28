from flask import Flask, redirect, request, render_template, url_for
import openai
import mysql.connector
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import secrets
import string

app = Flask(__name__, static_folder="static")
# Apply for an OpenAI API key and paste it here
openai.api_key = "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"

model_engine = "text-davinci-002"

# Connect to MySQL database
mydb = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="hello123",
    database="companydata",
    port="3307",
)
cursor = mydb.cursor()

generated_questions = []
formatted_questions = []
formatted_answers = []
formatted_questions_final = []
formatted_answers_final = []
emails = ["aakarshachugh23@gmail.com"]


# Render the company information form
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        print(request.form)
        name = request.form["name"]
        branch = request.form["branch"]
        email = request.form["email"]
        phone = request.form["phone"]
        prompt = request.form["prompt"]

        # print(name, branch, email, phone, prompt)
        # Insert company data into the database
        sql = (
            "INSERT INTO companies (name, branch, email, phone) VALUES (%s, %s, %s, %s)"
        )
        print(cursor.rowcount)
        values = (name, branch, email, phone)
        print(values)
        cursor.execute(sql, values)
        mydb.commit()

        # Retrieve the companyId of the inserted row
        companyId = cursor.lastrowid

        # Insert the prompt into the company_prompts table with the corresponding companyId value
        sql = "INSERT INTO company_prompts (companyId, prompt) VALUES (%s, %s)"
        print(cursor.rowcount)
        values = (companyId, prompt)
        print(values)
        cursor.execute(sql, values)
        mydb.commit()

        # generate questions using the generate_question method
        generated_questions = generate_question(prompt)
        # formatting the questions and answers using the format_generated_questions method
        formatted_questions, formatted_answers = format_generated_questions(
            generated_questions
        )

        print("Generated questions", generated_questions)
        print("Formatted questions", formatted_questions)
        print("Formatted answers", formatted_answers)

        # return "Form submitted"
        return redirect(url_for("survey_questions", prompt=prompt))
    else:
        return render_template("Company Interface.html")


@app.route("/survey_questions", methods=["GET", "POST"])
def survey_questions():
    # Generate the survey questions based on the prompt and display it on the page
    if request.method == "POST" and "generate_questions" in request.form:
        # Retrieve the prompt from the last inserted row in the company_prompts table
        sql = "SELECT prompt FROM company_prompts ORDER BY promptId DESC LIMIT 1"
        cursor.execute(sql)
        result = cursor.fetchone()
        prompt = result[0] if result else None

        if prompt is None:
            return "Error: No prompt found in the company_prompts table."

        # Handle generation of additional questions
        generated_questions = generate_question(prompt)
        global formatted_questions, formatted_answers
        formatted_questions, formatted_answers = format_generated_questions(
            generated_questions
        )
        return redirect(url_for("survey_questions"))

    elif request.method == "POST":
        # Print the form items
        for key, value in request.form.items():
            print(f"Key: {key}, Value: {value}")

        # Extract the questions and answers
        question_number = 1
        current_answers = []
        for key, value in request.form.items():
            if key.startswith("question"):
                formatted_questions_final.append(value)
            if current_answers:
                clean_answers = [
                    answer.strip("[]").replace("'", "").replace('"', "")
                    for answer in current_answers
                ]
                formatted_answers_final.append(clean_answers)
                current_answers = []
                question_number += 1
            elif key.startswith("answer"):
                current_answers.append(value)

        if current_answers:
            clean_answers = [
                answer.strip("[]").replace("'", "").replace('"', "")
                for answer in current_answers
            ]
            formatted_answers_final.append(clean_answers)

        print("Formatted Questions", formatted_questions_final)
        print("Formatted Answers", formatted_answers_final)

        companyId = cursor.lastrowid
        # Get the number of questions
        num_questions = len(formatted_questions_final)

        # Create a list with 10 elements, where the first element is the companyId
        values = [companyId]

        # Append the questions to the values list
        values.extend(formatted_questions_final)

        # Pad the values list with None for remaining columns
        values += [None] * (10 - num_questions)

        # Build the SQL query
        sql = "INSERT INTO Questions (companyId, question1, question2, question3, question4, question5, question6, question7, question8, question9, question10) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        # Execute the SQL query
        cursor.execute(sql, values)
        mydb.commit()

        return redirect(
            url_for(
                "finalize_questions",
                question_data=zip(formatted_questions_final, formatted_answers_final),
            )
        )

    else:
        return render_template(
            "SurveyQuestions.html",
            question_data=zip(formatted_questions, formatted_answers),
        )


@app.route("/finalize_questions", methods=["GET", "POST"])
def finalize_questions():
    if request.method == "POST":
        send_survey_invitations(emails)
        return "Survey has been sent to your email list"
    else:
        # Render the generated questions page

        return render_template(
            "GeneratedQuestions.html",
            question_data=zip(formatted_questions_final, formatted_answers_final),
        )


@app.route("/survey", methods=["GET", "POST"])
def survey():
    # Retrieve the token and email from the query parameters
    token = request.args.get("token")
    email = request.args.get("email")
    if request.method == "POST":
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        email = request.form["email"]
        agerange = request.form["agerange"]
        gender = request.form["gender"]
        race = request.form["race"]
        employmentstatus = request.form["employmentstatus"]

        # Insert data into the database
        sql = "INSERT INTO User (firstname, lastname, email, agerange, gender, race, employmentstatus) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (firstname, lastname, email, agerange, gender, race, employmentstatus)
        cursor.execute(sql, values)
        mydb.commit()

        # Return success message
        return "Your responses have been recorded"

    # Render the GeneratedQuestions.html page
    return render_template(
        "GeneratedQuestions.html",
        token=token,
        email=email,
        question_data=zip(formatted_questions_final, formatted_answers_final),
    )


# Define a function to generate questions based on the prompt and return them in a list
def generate_question(prompt):
    completions = openai.Completion.create(
        engine=model_engine,
        prompt="Please generate a distinct multiple-choice question for a user survey, with 4 options labeled 'a)', 'b)', 'c)', and 'd)'. The question should be based on the given prompt, but should not mention the name of the product unless specified. Additionally, please ensure that no generated question is repeated in any completion."
        + prompt,
        max_tokens=1024,
        n=2,
        stop=None,
        temperature=0.8,
    )
    # Define an empty list to store the generated questions
    questions = []
    # Loop through the generated questions
    for choice in completions.choices:
        # Store the text of the generated question
        question = choice.text.strip()

        # question = [''.join(q) for q in question]

        # Add the generated question to the list of questions
        questions.append(question)

    # Update the list of previously generated questions with the new questions
    generated_questions.extend(questions)

    # Return the list of generated questions
    return questions


def format_generated_questions(generated_questions):
    # formatted_questions = []
    # formatted_answers = []

    for question in generated_questions:
        # Extract the questions and format them to remove extra spaces
        question_text = question.split("?")[0].strip() + "?"
        formatted_questions.append(question_text)

        # Extract the options and format them to remove extra spaces
        options = re.split(r"[\n\r]+", question.split("?")[1].strip())
        if options:
            formatted_answers.append(
                [option.split(")")[1].strip() for option in options if option]
            )

    return formatted_questions, formatted_answers


def send_survey_invitations(emails):
    sender_email = "anav.chug18@gmail.com"  # Set the sender's email address
    subject = "Survey Invitation"  # Set the email subject

    for email in emails:
        # Generate a unique URL for each survey response
        survey_url = generate_survey_url(email)

        # Create the email content
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = email
        message["Subject"] = subject

        # Add the survey URL to the email body
        body = f"Dear recipient,\n\nPlease click the following link to fill out the survey:\n{survey_url}"
        message.attach(MIMEText(body, "plain"))

        # Convert the message to a string
        email_content = message.as_string()

        # Send the email
        smtp_server = "smtp.gmail.com"  # Set the SMTP server details
        smtp_port = 587  # Set the SMTP server port
        smtp_username = "anav.chug18@gmail.com"  # Set your SMTP username
        smtp_password = "wkgrpezmzbealdxb"  # Set your SMTP password, using this password so we dont get any authentication errors

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, email, email_content)


def generate_survey_url(email):
    # Generate a unique URL for each survey response based on the email
    # You can use a unique identifier or token here
    unique_token = generate_unique_token()

    # Construct the survey URL with the unique token
    survey_url = f"http://127.0.0.1:5000/survey?token={unique_token}&email={email}"

    return survey_url


def generate_unique_token(length=16):
    characters = string.ascii_letters + string.digits
    token = "".join(secrets.choice(characters) for _ in range(length))
    return token


if __name__ == "__main__":
    app.run(debug=True)
