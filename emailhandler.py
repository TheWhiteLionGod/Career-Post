from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

EMAIL = os.environ.get('EMAIL')
API = os.environ.get('SENDGRID')

def sendMail(name: str, toEmail: str, fromEmail: str, phoneNumber: str, mail: str) -> None:
    sendmail = Mail(
        from_email=EMAIL,
        to_emails=toEmail,
        subject='Someone Using Career Post Has Tried to Contact You',
        html_content=f'Name: {name}<br><br>Email: {fromEmail}<br><br>Phone Number: {phoneNumber}<br><br>Message:<br>{mail}'
    )

    sg = SendGridAPIClient(API)
    sg.send(sendmail)
