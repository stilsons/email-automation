import base64
from email.message import EmailMessage
from pathlib import Path

from src.config import (
    RECIPIENT_EMAIL,
    SENDER_EMAIL,
    SEND_EMAILS,
    TEST_MODE,
    config,
    require_send_config,
)
from src.gmail_client import GmailClient



def send_batch_email(zip_path: Path) -> bool:
    if not zip_path or not zip_path.exists():
        print("[EMAIL] Zip file does not exist.")
        return False

    try:
        require_send_config()
    except RuntimeError as exc:
        print(f"[EMAIL] {exc}")
        return False

    subject = f"For Dominick - {zip_path.stem}"
    body_text = config["send"]["body"]["text"].strip()
    signature_name = config["send"]["signature"]["name"].strip()
    body = f"{body_text}\n\nRegards,\n{signature_name}"

    print(f"[EMAIL] From: {SENDER_EMAIL}")
    print(f"[EMAIL] To: {RECIPIENT_EMAIL}")
    print(f"[EMAIL] Subject: {subject}")
    print(f"[EMAIL] Attachment: {zip_path.name}")

    if TEST_MODE or not SEND_EMAILS:
        print("[EMAIL] Dry run mode. Email not sent.")
        return False

    try:
        message = EmailMessage()
        message["To"] = RECIPIENT_EMAIL
        message["From"] = SENDER_EMAIL
        message["Subject"] = subject
        message.set_content(body)

        with open(zip_path, "rb") as f:
            file_data = f.read()

        message.add_attachment(
            file_data,
            maintype="application",
            subtype="zip",
            filename=zip_path.name,
        )

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        gmail_client = GmailClient()
        service = gmail_client.service

        service.users().messages().send(
            userId="me",
            body={"raw": raw_message},
        ).execute()

        print("[EMAIL] Email sent successfully via Gmail API.")
        return True

    except Exception as exc:
        print(f"[EMAIL] Failed to send email via Gmail API: {exc}")
        return False
