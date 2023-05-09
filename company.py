from flask import Flask, redirect, request, render_template, url_for
import openai
import mysql.connector

app = Flask(__name__)
# Apply for an OpenAI API key and paste it here
openai.api_key = "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"

model_engine = "text-davinci-002"
generated_questions = []

# Connect to MySQL database
mydb = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="hello123",
    database="companydata",
    port="3307"
)
cursor = mydb.cursor()

# Render the company information form
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print(request.form)
        name = request.form['name']
        branch = request.form['branch']
        email = request.form['email']
        phone = request.form['phone']
        prompt = request.form['prompt']

        # Insert company data into the database
        sql = "INSERT INTO companies (name, branch, email, phone, prompt) VALUES (%s, %s, %s, %s, %s)"
        values = (name, branch, email, phone, prompt)
        cursor.execute(sql, values)
        mydb.commit()

        # Generate questions based on the prompt and display it on the page
        generated_questions = generate_question(prompt)

        # Redirect to the generated_questions function to display the survey
        return redirect(url_for('generatedQuestions', generated_questions=generated_questions))
    return render_template('Company Interface.html')

# Render the generated questions form
@app.route('/generated_questions', methods=['GET', 'POST'])
def generatedQuestions(): 
    if request.method == 'POST':
        # Process the user survey form data on form submission
        #try:
            # Get form data
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            email = request.form['email']
            agerange = request.form['agerange']
            gender = request.form['gender']
            race = request.form['race']
            employmentstatus = request.form['employmentstatus']

            # Insert data into the database
            sql = "INSERT INTO User (firstname, lastname, email, agerange, gender, race, employmentstatus) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            values = (firstname, lastname, email, agerange, gender, race, employmentstatus)
            cursor.execute(sql, values)
            mydb.commit()

            # Return success message
            return 'Survey submitted successfully'

        #except:
            # Return error message if survey data could not be submitted
            #return 'Error submitting survey data'

    else:
        # Get the generated questions from the query string parameters
        generated_questions = request.args.getlist('generated_questions')
        print(generated_questions)
        print("Hello World")
    
        # Render the generated questions template
        return render_template('GeneratedQuestions.html', generated_questions=generated_questions)

# Define a function to generate questions based on the prompt and return them in a list
def generate_question(prompt):
    completions = openai.Completion.create(
        engine=model_engine,
        prompt="Please generate a distinct multiple-choice question for a user survey, with 4 options labeled 'a)', 'b)', 'c)', and 'd)'. The question should be based on the given prompt, but should not mention the name of the product unless specified. Additionally, please ensure that no generated question is repeated in any completion." + prompt,
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

        #question = [''.join(q) for q in question]

        # Add the generated question to the list of questions
        questions.append(question)

    # Update the list of previously generated questions with the new questions
    generated_questions.extend(questions)

    # Return the list of generated questions
    return questions

if __name__ == '__main__':
    app.run(debug=True)
