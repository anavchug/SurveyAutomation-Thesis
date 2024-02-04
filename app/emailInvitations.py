from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import secrets
import string

def send_survey_invitations(emails, companyId, promptId):
    sender_email = "anav.chug18@gmail.com"  # Set the sender's email address
    subject = "Survey Invitation"  # Set the email subject

    for email in emails:
        # Generate a unique URL for each survey response
        survey_url = generate_survey_url(email, companyId, promptId)

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


def generate_survey_url(email, companyId, promptId):
    # Generate a unique URL for each survey response based on the email
    # You can use a unique identifier or token here
    unique_token = generate_unique_token()

    # Construct the survey URL with the unique token
    survey_url = f"http://127.0.0.1:5000/survey?token={unique_token}&email={email}&companyId={companyId}&promptId={promptId}"

    return survey_url


def generate_unique_token(length=16):
    characters = string.ascii_letters + string.digits
    token = "".join(secrets.choice(characters) for _ in range(length))
    return token
