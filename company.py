from flask import Flask, redirect, request, render_template, url_for
import openai
import mysql.connector
import re

app = Flask(__name__)
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

        generated_questions = generate_question(prompt)
        print("Generated questions", generated_questions)

        for question in generated_questions:
            # Extract the questions and format them to remove extra spaces
            question_text = question.split("?")[0].strip() + "?"
            formatted_questions.append(question_text)
            print("Formatted questions", formatted_questions)

            # Extract the options and format them to remove extra spaces
            options = re.split(r"[\n\r]+", question.split("?")[1].strip())
            if options:
                formatted_answers.append(
                    [option.split(")")[1].strip() for option in options if option]
                )
            print("Formatted answers", formatted_answers)

        # return "Form submitted"
        return redirect(url_for("survey_questions"))
    else:
        return render_template("Company Interface.html")


@app.route("/survey_questions", methods=["GET", "POST"])
def survey_questions():
    # Generate the survey questions based on the prompt and display it on the page
    if request.method == "POST":
        # Extract the questions to be deleted
        delete_list = []
        for key, value in request.form.items():
            if key.startswith("delete_"):
                delete_list.append(int(key.split("_")[1]))

        # Remove the deleted questions from the formatted lists
        formatted_questions_final = []
        formatted_answers_final = []
        for i, question in enumerate(formatted_questions):
            if i not in delete_list:
                formatted_questions_final.append(question)
                formatted_answers_final.append(formatted_answers[i])
                print(formatted_questions_final)
                print(formatted_answers_final)

        # Update the global formatted_questions and formatted_answers lists
        # global formatted_questions
        # global formatted_answers
        # formatted_questions = formatted_questions_final
        # formatted_answers = formatted_answers_final

        # Insert the remaining questions into the database
        question1 = formatted_questions_final[0]
        question2 = formatted_questions_final[1]
        companyId = cursor.lastrowid
        sql = "INSERT INTO Questions (companyId, question1, question2) VALUES (%s, %s, %s)"
        values = (companyId, question1, question2)
        cursor.execute(sql, values)
        mydb.commit()

        return redirect(url_for("finalize_questions"))
    else:
        return render_template(
            "SurveyQuestions.html",
            question_data=zip(formatted_questions, formatted_answers),
        )


@app.route("/finalize_questions", methods=["GET", "POST"])
def finalize_questions():
    if request.method == "POST":
        # Redirect the user to generated Questions
        # return redirect(url_for("generatedQuestions"))
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

    else:
        # Render the generated questions page
        return render_template(
            "GeneratedQuestions.html",
            question_data=zip(formatted_questions, formatted_answers),
        )


# Render the generated questions form

"""
@app.route("/generated_questions", methods=["GET", "POST"])
def generatedQuestions():
    if request.method == "POST":
        # Process the user survey form data on form submission
        # Get form data
        return "Survey Submitted"

    else:
        # Get the generated questions from the query string parameters
        formatted_questions = request.args.getlist("formatted_questions")
        formatted_answers = request.args.getlist("formatted_answers")
        print(generated_questions)

        # Render the generated questions template
        return render_template(
            "GeneratedQuestions.html",
            formatted_questions=formatted_questions,
            formatted_answers=formatted_answers,
        )
"""


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


if __name__ == "__main__":
    app.run(debug=True)
