import imaplib
import email
import os
import zipfile
import shutil
import sqlite3

import poplib
from email import parser

POP_SERVER = "pop.gmail.com"
POP_PORT = 995
EMAIL_USER = "giscardntchinda@email.com"
EMAIL_PASS = "iaju sgdx tatv qwth"

# SAVE_DIR = r"C:\temp\incoming_zip"      
# DEST_DIR = r"C:\db_storage"


def get_latest_mail():
    pop_conn = poplib.POP3_SSL(POP_SERVER, POP_PORT)
    pop_conn.user(EMAIL_USER)
    pop_conn.pass_(EMAIL_PASS)

    num_messages = len(pop_conn.list()[1])
    print("Total messages:", num_messages)

    # download the last / newest email
    raw_email = b"\n".join(pop_conn.retr(num_messages)[1])
    pop_conn.quit()

    return parser.Parser().parsestr(raw_email.decode("utf-8", errors="ignore"))
def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
        for name in z.namelist():
            if name.endswith(".db"):
                return os.path.join(extract_to, name)
    return None

def move_db(db_path, destination_folder):
    final_path = os.path.join(destination_folder, os.path.basename(db_path))
    shutil.move(db_path, final_path)
    return final_path


def download_latest_zip():
    SAVE_DIR = r"C:\posSave\incoming_zip"
    os.makedirs(SAVE_DIR, exist_ok=True)
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    # Connect to IMAP
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("INBOX")

    # Search all emails
    result, data = mail.search(None, "ALL")
    mail_ids = data[0].split()

    if not mail_ids:
        print("No emails found.")
        return None
    
    latest_id = mail_ids[-1]  # last email is the newest
    result, msg_data = mail.fetch(latest_id, "(RFC822)")

    raw_email = msg_data[0][1] # type: ignore
    msg = email.message_from_bytes(raw_email) # type: ignore

    # Look for attachments
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue

        if part.get("Content-Disposition") is None:
            continue

        filename = part.get_filename()
        if filename and filename.endswith(".zip"):
            zip_path = os.path.join(SAVE_DIR, filename)
            with open(zip_path, "wb") as f:
                payload = part.get_payload(decode=True)
                if payload is None:
                    # no payload to write, skip this part
                    continue
                if isinstance(payload, str):
                    payload = payload.encode()
                elif not isinstance(payload, bytes):
                    payload = bytes(payload)
                f.write(payload)
            return zip_path

    return None


def process_latest_backup():
    db_path = r"c:/posdatabase/config.db"
    folder_conn = sqlite3.connect(db_path)
    folder_cursor = folder_conn.cursor()
    folder_cursor.execute("SELECT * FROM configurations_folders")
    folder_rows = folder_cursor.fetchone()
    folder_conn.close()

    DEST_DIR = folder_rows[2]

    SAVE_DIR = r"C:\posSave\incoming_zip"
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    zip_file = download_latest_zip()

    if not zip_file:
        print("No ZIP attachment found.")
        return None

    print("ZIP downloaded:", zip_file)

    # Extract the DB
    extracted_db = extract_zip(zip_file, SAVE_DIR)
    if not extracted_db:
        print("No DB found inside ZIP.")
        return None

    print("Extracted DB:", extracted_db)

    # Remove old DB in destination
    clean_destination(DEST_DIR)

    # Move the new DB into destination
    final_db = move_db(extracted_db, DEST_DIR)
    print("New DB installed at:", final_db)

    # Remove ZIP after processing
    os.remove(zip_file)

    return final_db
