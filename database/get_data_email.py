from math import log
import poplib
import os
import time
import zipfile
import shutil
from email import parser
from email import policy
import sqlite3
import logging
import sys

from database.models import POPConfig


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.FileHandler('fastapi.log', encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_pop_credentials():
    """
    Fetch POP server credentials from environment variables.
    Returns a tuple (server, port, username, password).
    Raises ValueError if any are missing.
    """
    try: 

        LOCAL_DB_PATH = r"C:\poswaza\temp\db\pos_local.db"

        conn = sqlite3.connect(LOCAL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT server, username, password, port FROM pop_config LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError("POP configuration not found in database.")
        return row[0], row[3], row[1], row[2]
    except Exception as e:
        logger.error(f"Error fetching POP credentials: {e}")
        return None, None, None, None

    
# ---------- CONFIG ----------
# POP_SERVER = "pop.gmail.com"   # change if needed
# POP_PORT = 995
# EMAIL_USER = "giscardntchinda@gmail.com"
# EMAIL_PASS = "yzeq tafx waik ihqh"

pop_data = fetch_pop_credentials()

POP_SERVER = pop_data[0]
POP_PORT = pop_data[1]
EMAIL_USER = pop_data[2]
EMAIL_PASS = pop_data[3]

TEMP_DIR = r"C:\temp\incoming_zip"   # temporary storage for zip + extraction
DEST_DIR = rf"C:\poswaza\temp\db"
# ---------- UTIL ----------

def ensure_folder(path):
    os.makedirs(path, exist_ok=True)
    return path

def wait_until_file_free(path, timeout=10, poll=0.25):
    """
    Wait until a file can be opened for reading (not locked).
    Returns True if file is free within timeout, else False.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            with open(path, "rb"):
                return True
        except (PermissionError, OSError):
            time.sleep(poll)
    return False

# ---------- DB file helpers ----------

def clean_destination(folder):
    """
    Remove ONLY local_data.db from 'folder'. Creates the folder if missing.
    """
    ensure_folder(folder)
    target = os.path.join(folder, "local_data.db")

    if os.path.exists(target):
        try:
            os.remove(target)
        except PermissionError:
            if wait_until_file_free(target, timeout=5):
                try:
                    os.remove(target)
                except Exception as e:
                    logger.error(f"Failed to remove locked DB {target}: {e}")
            else:
                logger.error(f"Could not remove locked DB {target}")


def move_db(src_path, destination_folder, retries=5, delay=0.5):
    """
    Move src_path (a .db file) into destination_folder.
    Retries a few times on PermissionError (Windows).
    Returns path to moved file on success, else raises.
    """
    ensure_folder(destination_folder)
    final_path = os.path.join(destination_folder, os.path.basename(src_path))

    for attempt in range(1, retries + 1):
        try:
            # Use shutil.move (will move across filesystems)
            shutil.move(src_path, final_path)
            return final_path
        except PermissionError as e:
            print(f"PermissionError moving DB (attempt {attempt}/{retries}): {e}")
            time.sleep(delay)
        except FileNotFoundError as e:
            # Source disappeared; nothing to move
            raise
    # final attempt: try copy + remove (may still fail)
    try:
        shutil.copy2(src_path, final_path)
        os.remove(src_path)
        return final_path
    except Exception as e:
        raise RuntimeError(f"Failed to move DB after retries: {e}")

def extract_zip(zip_path, extract_to):
    """
    Extract zip_path into extract_to and return the first .db found (full path),
    or None if no .db inside.
    """
    ensure_folder(extract_to)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
        for name in z.namelist():
            if name.lower().endswith(".db"):
                # If the ZIP contains directories, normalize the path
                return os.path.join(extract_to, name)
    return None


def email_contains_zip(msg):
    """
    Check if email contains a ZIP attachment.
    Now with detailed debugging and more thorough detection.
    """
    logger.info("   Scanning email parts for ZIP...")
    has_zip = False
    
    for part in msg.walk():
        if part.is_multipart():
            continue
        
        filename = part.get_filename()
        content_type = part.get_content_type()
        content_disposition = part.get("Content-Disposition", "")
        
        # Debug: Show what we found
        logger.info(f"    Part: type={content_type}, filename={filename}, disposition={content_disposition[:50] if content_disposition else 'None'}")
        
        # Check 1: Filename ends with .zip
        if filename and filename.lower().endswith(".zip"):
            logger.info(f"    Found ZIP by filename: {filename}")
            has_zip = True
            
        # Check 2: Content type is explicitly application/zip
        elif content_type == "application/zip":
            logger.info(f"     Found ZIP by content-type: application/zip")
            has_zip = True
            
        # Check 3: octet-stream with .zip filename
        elif content_type == "application/octet-stream" and filename:
            if filename.lower().endswith(".zip"):
                logger.info(f"     Found ZIP in octet-stream: {filename}")
                has_zip = True
            else:
                logger.info(f"     octet-stream but not .zip: {filename}")
                
        # Check 4: Try to detect zip by magic bytes (ZIP files start with 'PK')
        elif content_type == "application/octet-stream" or "attachment" in content_disposition.lower():
            try:
                payload = part.get_payload(decode=True)
                if payload and len(payload) > 4:
                    # Check for ZIP magic bytes: 'PK\x03\x04' or 'PK\x05\x06'
                    if payload[:2] == b'PK':
                        logger.info(f"     Found ZIP by magic bytes (PK signature)")
                        has_zip = True
            except Exception as e:
                logger.error(f"     Error checking payload: {e}")
    
    return has_zip

# ---------- POP3 + email helpers ----------

def get_latest_mail_with_zip():
    pop_conn = poplib.POP3_SSL(POP_SERVER, POP_PORT, timeout=30) # type: ignore
    pop_conn.user(EMAIL_USER) # type: ignore
    pop_conn.pass_(EMAIL_PASS) # type: ignore

    resp, items, octets = pop_conn.list()
    total = len(items)
    logger.info(f"Total messages: {total}")

    if total == 0:
        pop_conn.quit()
        return None

    # Iterate from most recent backwards
    for i in range(total, 0, -1):
        logger.info(f"\nChecking email #{i} ...")

        resp, lines, octets = pop_conn.retr(i)
        raw_message = b"\r\n".join(lines)
        msg = parser.BytesParser(policy=policy.default).parsebytes(raw_message)

        subject = msg.get("Subject", "No Subject")
        from_addr = msg.get("From", "Unknown")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  From: {from_addr}")

        # does this email contain a ZIP?
        if email_contains_zip(msg):
            logger.info(f" Found ZIP in message #{i}")
            pop_conn.quit()
            return msg
        else:
            logger.info(f" No ZIP found in message #{i}")

    logger.info("\n No emails with ZIP attachments found!")
    pop_conn.quit()
    return None

def extract_zip_from_email(msg, save_dir):
    ensure_folder(save_dir)
    for part in msg.walk():
        if part.is_multipart():
            continue

        filename = part.get_filename()
        content_type = part.get_content_type()
        disp = part.get("Content-Disposition", "")

        logger.debug("DEBUG -> content_type:", content_type,
              "filename:", filename,
              "disposition:", disp)

        # CASE 1: Standard attachment
        if filename and filename.lower().endswith(".zip"):
            save_path = os.path.join(save_dir, filename)
            with open(save_path, "wb") as fh:
                fh.write(part.get_payload(decode=True))
            return save_path

        # CASE 2: No filename but ZIP type
        if content_type == "application/zip":
            save_path = os.path.join(save_dir, "backup.zip")
            with open(save_path, "wb") as fh:
                fh.write(part.get_payload(decode=True))
            return save_path

        # CASE 3: Hidden ZIP in octet-stream
        if content_type == "application/octet-stream":
            # try detect filename
            if filename:
                save_path = os.path.join(save_dir, filename)
            else:
                save_path = os.path.join(save_dir, "backup.zip")

            with open(save_path, "wb") as fh:
                fh.write(part.get_payload(decode=True))
            return save_path
        
        payload = part.get_payload(decode=True)
        if payload and len(payload) > 4 and payload[:2] == b'PK':
            # This looks like a ZIP file
            if filename:
                save_path = os.path.join(save_dir, filename)
            else:
                save_path = os.path.join(save_dir, "backup.zip")
            
            with open(save_path, "wb") as fh:
                fh.write(payload)
            logger.debug(f"DEBUG -> Saved ZIP detected by magic bytes: {save_path}")
            return save_path

    return None

# ---------- Main pipeline ----------

def fetch_db_from_latest_email():
    """
    Entire pipeline:
    - fetch latest email via POP3
    - find .zip attachment and save it
    - extract .db from zip
    - clean destination folder (remove old .db files)
    - move new .db into destination
    Returns final DB path or None.
    """
    

    

    ensure_folder(TEMP_DIR)
    ensure_folder(DEST_DIR)

    print("Connecting to POP3 and fetching latest email...")
    msg = get_latest_mail_with_zip()
    if msg is None:
        logger.info("No emails found with ZIP attachments.")
        return None

    logger.info("\nSearching for ZIP attachment...")
    zip_path = extract_zip_from_email(msg, TEMP_DIR)
    if not zip_path:
        logger.info("No ZIP attachment found in latest email.")
        return None

    logger.info(f"ZIP downloaded to: {zip_path}")

    logger.info("Extracting ZIP...")
    extracted_db = extract_zip(zip_path, TEMP_DIR)
    if not extracted_db or not os.path.exists(extracted_db):
        logger.info("No .db found inside ZIP.")
        # cleanup zip if desired
        try:
            os.remove(zip_path)
        except Exception:
            pass
        return None

    # Normalize path (zip may contain folder structure)
    extracted_db = os.path.normpath(extracted_db)
    logger.info(f"Extracted DB path: {extracted_db}")

    # Wait until the extracted DB file is free (not locked)
    if not wait_until_file_free(extracted_db, timeout=10):
        logger.warning("Warning: extracted DB may be locked. Proceeding to attempt move anyway.")
    # Clean existing DBs in destination
    logger.info(f"Cleaning destination folder: {DEST_DIR}")
    clean_destination(DEST_DIR)

    # Move the new DB into destination
    logger.info("Moving DB to destination...")
    try:
        final_db = move_db(extracted_db, DEST_DIR)
    except FileNotFoundError:
        logger.error("Extracted .db not found when attempting to move (race condition).")
        final_db = None
    except Exception as e:
        logger.error(f"Failed to move DB: {e}")
        final_db = None

    # Remove zip file
    try:
        os.remove(zip_path)
    except Exception:
        pass

    if final_db:
        logger.info(f"New DB installed at: {final_db}")
    else:
        logger.info("DB installation failed.")

    return final_db

# ---------- If run as script ----------
if __name__ == "__main__":
    result = fetch_db_from_latest_email()
    print("Result:", result)
