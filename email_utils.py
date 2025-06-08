import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = ""  # замени на свой
SMTP_PASSWORD = "your_password"         # или app password

def send_payment_email(to_email: str, amount: int, currency: str):
    subject = "Спасибо за оплату!"
    body = f"Мы получили ваш платёж на сумму {amount / 100:.2f} {currency.upper()}."
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, to_email, msg.as_string())