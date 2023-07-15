from flask import Flask, redirect, request, render_template, url_for, session
import openai
import mysql.connector
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import secrets
import string
import pandas as pd
import plotly.express as px

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
emails = ["aakarshachugh23@gmail.com", "aakarshachugh19@gmail.com"]

# Render the login page 
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username and password are valid in the database
        query = "SELECT * FROM Accounts WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()

        if user:
            # Store the user's information in the session
            session['username'] = user[1]
            return redirect('/dashboard')
        else:
            return 'Invalid username or password'

    return render_template("login.html")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username is already taken
        query = "SELECT * FROM Accounts WHERE username = %s"
        cursor.execute(query, (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            return 'Username already exists'
        else:
            # Insert the new user into the database
            query = "INSERT INTO Accounts (username, password) VALUES (%s, %s)"
            cursor.execute(query, (username, password))
            mydb.commit()

            # Store the user's information in the session
            session['username'] = username
            return redirect('/')

    return render_template("register.html")


@app.route('/dashboard')
def dashboard():
    # Check if the user is logged in by checking the session
    if 'username' in session:
        username = session['username']
        return render_template("CompanyDashboard.html", username = username)
    else:
        return redirect('/')


@app.route('/logout')
def logout():
    # Clear the session and redirect to the login page
    session.clear()
    return redirect('/')

@app.route("/company", methods=["GET", "POST"])
def company():
    if request.method == "POST":
        name = request.form["name"]
        branch = request.form["branch"]
        email = request.form["email"]
        phone = request.form["phone"]
        prompt = request.form["prompt"]

        # Check if the company already exists in the database
        query = "SELECT companyId FROM companies WHERE name = %s AND branch = %s"
        values = (name, branch)
        cursor.execute(query, values)
        existing_company = cursor.fetchone()

        if existing_company:
            companyId = existing_company[0]  # Retrieve the existing companyId
        else:
            # Insert company data into the database
            sql = "INSERT INTO companies (name, branch, email, phone) VALUES (%s, %s, %s, %s)"
            values = (name, branch, email, phone)
            cursor.execute(sql, values)
            mydb.commit()

            # Retrieve the companyId of the inserted row
            companyId = cursor.lastrowid

        # Insert the prompt into the company_prompts table with the corresponding companyId value
        sql = "INSERT INTO company_prompts (companyId, prompt) VALUES (%s, %s)"
        values = (companyId, prompt)
        cursor.execute(sql, values)
        mydb.commit()

        # Generate questions using the generate_question method
        generated_questions = generate_question(prompt)
        # Format the questions and answers using the format_generated_questions method
        formatted_questions, formatted_answers = format_generated_questions(
            generated_questions
        )

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
    current_route = "/finalize_questions"
    if request.method == "POST":
        send_survey_invitations(emails)
        return "Survey has been sent to your email list"
    else:
        # Render the generated questions page
        return render_template(
            "GeneratedQuestions.html",
            question_data=zip(formatted_questions_final, formatted_answers_final),
            current_route=current_route,
        )


@app.route("/survey", methods=["GET", "POST"])
def survey():
    answers = request.form
    # Retrieve the token and email from the query parameters
    token = request.args.get("token")
    email = request.args.get("email")
    current_route = "/survey"

    if request.method == "POST":
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        email = request.form["email"]
        agerange = request.form["agerange"]
        gender = request.form["gender"]
        race = request.form["race"]
        employmentstatus = request.form["employmentstatus"]

        companyId = cursor.lastrowid
        # userId = cursor.lastrowid
        quesId = cursor.lastrowid
        promptId = cursor.lastrowid

        # Insert data into the database
        sql = "INSERT INTO User (firstname, lastname, email, agerange, gender, race, employmentstatus) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (firstname, lastname, email, agerange, gender, race, employmentstatus)
        cursor.execute(sql, values)
        mydb.commit()

        # Retrieve the form data
        form_data = request.form
        print("form daata: ", form_data)
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

        # Retrieve and append the responses to the values list
        user_data_keys = [
            "firstname",
            "lastname",
            "email",
            "agerange",
            "gender",
            "race",
            "employmentstatus",
        ]
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
        return render_template(
            "GeneratedQuestions.html",
            token=token,
            email=email,
            question_data=zip(formatted_questions_final, formatted_answers_final),
            current_route=current_route,
        )

# Define a route for the home page
@app.route("/analysis")
def home():
    # Fetch data from the MySQL database
    cursor = mydb.cursor()
    cursor.execute(
        "SELECT * FROM Survey INNER JOIN User ON Survey.UserId = User.userId"
    )
    data = cursor.fetchall()
    print("Initial data:", data)
    cursor.close()

    # Convert data to DataFrame
    column_names = [
        "SurveyID",
        "CompanyId",
        "UserId",
        "QuesId",
        "PromptId",
        "response1",
        "response2",
        "response3",
        "response4",
        "response5",
        "response6",
        "response7",
        "response8",
        "response9",
        "response10",
        "userId",
        "FirstName",
        "LastName",
        "Email",
        "AgeRange",
        "Gender",
        "Race",
        "EmploymentStatus",
    ]
    data = pd.DataFrame(data, columns=column_names)
    print("Formatted after using Pandas:", data)

    # Extract the response columns
    responses = data[
        [
            "response1",
            "response2",
            "response3",
            "response4",
            "response5",
            "response6",
            "response7",
            "response8",
            "response9",
            "response10",
        ]
    ]

    # extract the demographic columns
    demographics = data[["AgeRange", "Gender", "Race", "EmploymentStatus"]]
    print(demographics)

    # Retrieve questions from the Questions table
    cursor = mydb.cursor()
    cursor.execute(
        "SELECT QuesId, Question1, Question2, Question3, Question4, Question5, Question6, Question7, Question8, Question9, Question10 FROM Questions"
    )
    questions_data = cursor.fetchall()
    print(questions_data)
    cursor.close()

    # Create a dictionary to map question IDs to question texts
    question_mapping = {
        row[0]: [q for q in row[1:] if q is not None] for row in questions_data
    }
    print(question_mapping)

    # Create a bar chart for each response column
    charts = []
    question_texts = []  # List to store question texts
    index = 0
    i = 1

    for column in responses.columns:
        # Filter out empty responses
        non_empty_responses = responses[column].dropna()

        # Proceed only if there are non-empty responses
        if not non_empty_responses.empty:
            question_id = int(
                column[8:]
            )  # Extract the question ID from the column name
            question_texts.extend(question_mapping.get(question_id, []))

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
        "index.html",
        graphJSONs=graphJSONs,
        num_charts=len(charts),
        question_mapping=question_mapping,
        question_texts=question_texts,
    )

@app.route("/demographics/<int:question_id>")
def demographics(question_id):
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
    GROUP BY
        U.AgeRange,
        S.{response_column}
    """

    cursor_age.execute(age_query.format(question_id=question_id, response_column=f"response{question_id}"))
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
    GROUP BY
        U.Gender,
        S.{response_column}
    """

    cursor_gender.execute(gender_query.format(question_id=question_id, response_column=f"response{question_id}"))
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
    GROUP BY
        U.Race,
        S.{response_column}
    """

    cursor_race.execute(race_query.format(question_id=question_id, response_column=f"response{question_id}"))
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
    GROUP BY
        U.EmploymentStatus,
        S.{response_column}
    """
    cursor_employment.execute(employmentStatus_query.format(question_id=question_id, response_column=f"response{question_id}"))
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
    app.secret_key = 'mykeyistheweirdestkeyevercreated#4322'
    app.config['SESSION_TYPE'] = 'filesystem'

    app.run(debug=True)
    app.run()
