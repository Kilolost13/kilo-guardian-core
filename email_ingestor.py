import imaplib
import email
import time
import requests
import os
import logging
from email.header import decode_header

# Configuration - You will need to set these env vars or I can add a config file
GMAIL_USER = os.environ.get("KILO_EMAIL_USER", "your-email@gmail.com")
GMAIL_PASS = os.environ.get("KILO_EMAIL_PASS", "your-app-password")
IMAP_SERVER = "imap.gmail.com"
TARGET_LABEL = "To Kilo"  # The folder Kilo will watch
BRAIN_URL = "http://localhost:9004/chat"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmailIngestor")

def clean_text(text):
    return "".join(i for i in text if ord(i) < 128)

def process_emails():
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_USER, GMAIL_PASS)
        
        # Select the label
        status, messages = mail.select(f'"{TARGET_LABEL}"')
        if status != 'OK':
            logger.error(f"Could not find label: {TARGET_LABEL}")
            return 0

        # Search for all emails in this label
        res, data = mail.search(None, 'ALL')
        email_ids = data[0].split()
        
        if not email_ids:
            logger.info("No new emails in 'To Kilo' label.")
            return 0

        logger.info(f"Found {len(email_ids)} emails to process.")
        processed_count = 0

        for e_id in email_ids:
            # Fetch the email data
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    sender = msg.get("From")
                    body = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    # Send to AI Brain
                    full_content = f"Subject: {subject}\nFrom: {sender}\n\n{body}"
                    payload = {"message": f"/remember FROM EMAIL: {full_content[:2000]}"} # Limit size for safety
                    
                    brain_res = requests.post(BRAIN_URL, json=payload, timeout=30)
                    
                    if brain_res.status_code == 200:
                        logger.info(f"Memorized email: {subject}")
                        # Move to Archive or Trash so we don't read it again
                        # For safety, we'll just remove the label 'To Kilo'
                        mail.store(e_id, '+FLAGS', '\\Deleted') 
                        processed_count += 1
                    
                    # POWER SAFETY: Rest between emails
                    time.sleep(3)

        mail.expunge()
        mail.logout()
        return processed_count

    except Exception as e:
        logger.error(f"Gmail Sync Error: {e}")
        return 0

if __name__ == "__main__":
    count = process_emails()
    print(f"Gmail Sync Complete. Processed {count} emails.")
