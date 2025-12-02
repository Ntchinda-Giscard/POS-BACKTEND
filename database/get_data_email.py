# from math import log
# import poplib
# import os
# import time
# import zipfile
# import shutil
# from email import parser
# from email import policy
# import sqlite3
# import logging
# import sys

# from database.models import POPConfig


# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
#     handlers=[
#         logging.FileHandler('fastapi.log', encoding="utf-8"),
#         logging.StreamHandler(sys.stdout)
#     ]
# )
# # logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)





# TEMP_DIR = r"C:\temp\incoming_zip"   # temporary storage for zip + extraction
# DEST_DIR = rf"C:\poswaza\temp\db"
# # ---------- UTIL ----------

# def ensure_folder(path):
#     os.makedirs(path, exist_ok=True)
#     return path

# def wait_until_file_free(path, timeout=10, poll=0.25):
#     """
#     Wait until a file can be opened for reading (not locked).
#     Returns True if file is free within timeout, else False.
#     """
#     start = time.time()
#     while time.time() - start < timeout:
#         try:
#             with open(path, "rb"):
#                 return True
#         except (PermissionError, OSError):
#             time.sleep(poll)
#     return False

# # ---------- DB file helpers ----------

# def clean_destination(folder):
#     """
#     Remove ONLY local_data.db from 'folder'. Creates the folder if missing.
#     """
#     ensure_folder(folder)
#     target = os.path.join(folder, "local_data.db")

#     if os.path.exists(target):
#         try:
#             os.remove(target)
#         except PermissionError:
#             if wait_until_file_free(target, timeout=5):
#                 try:
#                     os.remove(target)
#                 except Exception as e:
#                     logger.error(f"Failed to remove locked DB {target}: {e}")
#             else:
#                 logger.error(f"Could not remove locked DB {target}")


# def move_db(src_path, destination_folder, retries=5, delay=0.5):
#     """
#     Move src_path (a .db file) into destination_folder.
#     Retries a few times on PermissionError (Windows).
#     Returns path to moved file on success, else raises.
#     """
#     ensure_folder(destination_folder)
#     final_path = os.path.join(destination_folder, os.path.basename(src_path))

#     for attempt in range(1, retries + 1):
#         try:
#             # Use shutil.move (will move across filesystems)
#             shutil.move(src_path, final_path)
#             return final_path
#         except PermissionError as e:
#             print(f"PermissionError moving DB (attempt {attempt}/{retries}): {e}")
#             time.sleep(delay)
#         except FileNotFoundError as e:
#             # Source disappeared; nothing to move
#             raise
#     # final attempt: try copy + remove (may still fail)
#     try:
#         shutil.copy2(src_path, final_path)
#         os.remove(src_path)
#         return final_path
#     except Exception as e:
#         raise RuntimeError(f"Failed to move DB after retries: {e}")

# def extract_zip(zip_path, extract_to):
#     """
#     Extract zip_path into extract_to and return the first .db found (full path),
#     or None if no .db inside.
#     """
#     ensure_folder(extract_to)
#     with zipfile.ZipFile(zip_path, "r") as z:
#         z.extractall(extract_to)
#         for name in z.namelist():
#             if name.lower().endswith(".db"):
#                 # If the ZIP contains directories, normalize the path
#                 return os.path.join(extract_to, name)
#     return None


# def email_contains_zip(msg):
#     """
#     Check if email contains a ZIP attachment.
#     Now with detailed debugging and more thorough detection.
#     """
#     logger.info("   Scanning email parts for ZIP...")
#     has_zip = False
    
#     for part in msg.walk():
#         if part.is_multipart():
#             continue
        
#         filename = part.get_filename()
#         content_type = part.get_content_type()
#         content_disposition = part.get("Content-Disposition", "")
        
#         # Debug: Show what we found
#         logger.info(f"    Part: type={content_type}, filename={filename}, disposition={content_disposition[:50] if content_disposition else 'None'}")
        
#         # Check 1: Filename ends with .zip
#         if filename and filename.lower().endswith(".zip"):
#             logger.info(f"    Found ZIP by filename: {filename}")
#             has_zip = True
            
#         # Check 2: Content type is explicitly application/zip
#         elif content_type == "application/zip":
#             logger.info(f"     Found ZIP by content-type: application/zip")
#             has_zip = True
            
#         # Check 3: octet-stream with .zip filename
#         elif content_type == "application/octet-stream" and filename:
#             if filename.lower().endswith(".zip"):
#                 logger.info(f"     Found ZIP in octet-stream: {filename}")
#                 has_zip = True
#             else:
#                 logger.info(f"     octet-stream but not .zip: {filename}")
                
#         # Check 4: Try to detect zip by magic bytes (ZIP files start with 'PK')
#         elif content_type == "application/octet-stream" or "attachment" in content_disposition.lower():
#             try:
#                 payload = part.get_payload(decode=True)
#                 if payload and len(payload) > 4:
#                     # Check for ZIP magic bytes: 'PK\x03\x04' or 'PK\x05\x06'
#                     if payload[:2] == b'PK':
#                         logger.info(f"     Found ZIP by magic bytes (PK signature)")
#                         has_zip = True
#             except Exception as e:
#                 logger.error(f"     Error checking payload: {e}")
    
#     return has_zip

# # ---------- POP3 + email helpers ----------

# def get_latest_mail_with_zip(POP_SERVER, POP_PORT, EMAIL_USER, EMAIL_PASS):
    
#     pop_conn = poplib.POP3_SSL(POP_SERVER, POP_PORT, timeout=30) # type: ignore
#     pop_conn.user(EMAIL_USER) # type: ignore
#     pop_conn.pass_(EMAIL_PASS) # type: ignore

#     resp, items, octets = pop_conn.list()
#     total = len(items)
#     logger.info(f"Total messages: {total}")

#     if total == 0:
#         pop_conn.quit()
#         return None

#     # Iterate from most recent backwards
#     for i in range(total, 0, -1):
#         logger.info(f"\nChecking email #{i} ...")

#         resp, lines, octets = pop_conn.retr(i)
#         raw_message = b"\r\n".join(lines)
#         msg = parser.BytesParser(policy=policy.default).parsebytes(raw_message)

#         subject = msg.get("Subject", "No Subject")
#         from_addr = msg.get("From", "Unknown")
#         logger.info(f"  Subject: {subject}")
#         logger.info(f"  From: {from_addr}")

#         # does this email contain a ZIP?
#         if email_contains_zip(msg):
#             logger.info(f" Found ZIP in message #{i}")
#             pop_conn.quit()
#             return msg
#         else:
#             logger.info(f" No ZIP found in message #{i}")

#     logger.info("\n No emails with ZIP attachments found!")
#     pop_conn.quit()
#     return None

# def extract_zip_from_email(msg, save_dir):
#     ensure_folder(save_dir)
#     for part in msg.walk():
#         if part.is_multipart():
#             continue

#         filename = part.get_filename()
#         content_type = part.get_content_type()
#         disp = part.get("Content-Disposition", "")

#         logger.debug("DEBUG -> content_type:", content_type,
#               "filename:", filename,
#               "disposition:", disp)

#         # CASE 1: Standard attachment
#         if filename and filename.lower().endswith(".zip"):
#             save_path = os.path.join(save_dir, filename)
#             with open(save_path, "wb") as fh:
#                 fh.write(part.get_payload(decode=True))
#             return save_path

#         # CASE 2: No filename but ZIP type
#         if content_type == "application/zip":
#             save_path = os.path.join(save_dir, "backup.zip")
#             with open(save_path, "wb") as fh:
#                 fh.write(part.get_payload(decode=True))
#             return save_path

#         # CASE 3: Hidden ZIP in octet-stream
#         if content_type == "application/octet-stream":
#             # try detect filename
#             if filename:
#                 save_path = os.path.join(save_dir, filename)
#             else:
#                 save_path = os.path.join(save_dir, "backup.zip")

#             with open(save_path, "wb") as fh:
#                 fh.write(part.get_payload(decode=True))
#             return save_path
        
#         payload = part.get_payload(decode=True)
#         if payload and len(payload) > 4 and payload[:2] == b'PK':
#             # This looks like a ZIP file
#             if filename:
#                 save_path = os.path.join(save_dir, filename)
#             else:
#                 save_path = os.path.join(save_dir, "backup.zip")
            
#             with open(save_path, "wb") as fh:
#                 fh.write(payload)
#             logger.debug(f"DEBUG -> Saved ZIP detected by magic bytes: {save_path}")
#             return save_path

#     return None

# # ---------- Main pipeline ----------

# def fetch_db_from_latest_email(POP_SERVER, POP_PORT, EMAIL_USER, EMAIL_PASS):
#     """
#     Entire pipeline:
#     - fetch latest email via POP3
#     - find .zip attachment and save it
#     - extract .db from zip
#     - clean destination folder (remove old .db files)
#     - move new .db into destination
#     Returns final DB path or None.
#     """
    

    

#     ensure_folder(TEMP_DIR)
#     ensure_folder(DEST_DIR)

#     print("Connecting to POP3 and fetching latest email...")
#     msg = get_latest_mail_with_zip(POP_SERVER, POP_PORT, EMAIL_USER, EMAIL_PASS)
#     if msg is None:
#         logger.info("No emails found with ZIP attachments.")
#         return None

#     logger.info("\nSearching for ZIP attachment...")
#     zip_path = extract_zip_from_email(msg, TEMP_DIR)
#     if not zip_path:
#         logger.info("No ZIP attachment found in latest email.")
#         return None

#     logger.info(f"ZIP downloaded to: {zip_path}")

#     logger.info("Extracting ZIP...")
#     extracted_db = extract_zip(zip_path, TEMP_DIR)
#     if not extracted_db or not os.path.exists(extracted_db):
#         logger.info("No .db found inside ZIP.")
#         # cleanup zip if desired
#         try:
#             os.remove(zip_path)
#         except Exception:
#             pass
#         return None

#     # Normalize path (zip may contain folder structure)
#     extracted_db = os.path.normpath(extracted_db)
#     logger.info(f"Extracted DB path: {extracted_db}")

#     # Wait until the extracted DB file is free (not locked)
#     if not wait_until_file_free(extracted_db, timeout=10):
#         logger.warning("Warning: extracted DB may be locked. Proceeding to attempt move anyway.")
#     # Clean existing DBs in destination
#     logger.info(f"Cleaning destination folder: {DEST_DIR}")
#     clean_destination(DEST_DIR)

#     # Move the new DB into destination
#     logger.info("Moving DB to destination...")
#     try:
#         final_db = move_db(extracted_db, DEST_DIR)
#     except FileNotFoundError:
#         logger.error("Extracted .db not found when attempting to move (race condition).")
#         final_db = None
#     except Exception as e:
#         logger.error(f"Failed to move DB: {e}")
#         final_db = None

#     # Remove zip file
#     try:
#         os.remove(zip_path)
#     except Exception:
#         pass

#     if final_db:
#         logger.info(f"New DB installed at: {final_db}")
#     else:
#         logger.info("DB installation failed.")

#     return final_db

# # ---------- If run as script ----------
# # if __name__ == "__main__":
#     # result = fetch_db_from_latest_email()
# #     print("Result:", result)



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
import json
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.FileHandler('fastapi.log', encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

TEMP_DIR = r"C:\temp\incoming_zip"
DEST_DIR = rf"C:\poswaza\temp\db"

# ---------- UTIL ----------

def ensure_folder(path):
    os.makedirs(path, exist_ok=True)
    return path

def wait_until_file_free(path, timeout=10, poll=0.25):
    """Wait until a file can be opened for reading (not locked)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with open(path, "rb"):
                return True
        except (PermissionError, OSError):
            time.sleep(poll)
    return False

def is_db_file_empty(db_path):
    """Check if local_data.db exists and has data in sync_state table."""
    if not os.path.exists(db_path):
        return True
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sync_state")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    except Exception as e:
        logger.error(f"Error checking DB: {e}")
        return True

# ---------- DB file helpers ----------

def clean_destination(folder):
    """Remove ONLY local_data.db from 'folder'. Creates the folder if missing."""
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
    """Move src_path (a .db file) into destination_folder."""
    ensure_folder(destination_folder)
    final_path = os.path.join(destination_folder, os.path.basename(src_path))

    for attempt in range(1, retries + 1):
        try:
            shutil.move(src_path, final_path)
            return final_path
        except PermissionError as e:
            logger.info(f"PermissionError moving DB (attempt {attempt}/{retries}): {e}")
            time.sleep(delay)
        except FileNotFoundError as e:
            raise

    try:
        shutil.copy2(src_path, final_path)
        os.remove(src_path)
        return final_path
    except Exception as e:
        raise RuntimeError(f"Failed to move DB after retries: {e}")

def extract_zip(zip_path, extract_to):
    """Extract zip_path into extract_to. Returns dict with extracted files."""
    ensure_folder(extract_to)
    extracted_files = {}
    
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
        for name in z.namelist():
            full_path = os.path.join(extract_to, name)
            if name.lower().endswith(".db"):
                extracted_files['db'] = full_path
            elif name.lower().endswith(".csv"):
                table_name = Path(name).stem
                extracted_files[table_name] = full_path
    
    return extracted_files

def detect_sync_type(msg, zip_contents):
    """
    Determine if this is FIRST SYNC (full DB) or DELTA SYNC (changes only).
    Returns 'full' or 'delta'
    """
    subject = msg.get("Subject", "").upper()
    
    # Check email subject for sync type indicators
    if "FULL DATABASE" in subject or "INITIAL" in subject:
        logger.info("[v0] Detected FULL DATABASE sync from subject")
        return 'full'
    
    if "DELTA" in subject or "CHANGES" in subject:
        logger.info("[v0] Detected DELTA CHANGES sync from subject")
        return 'delta'
    
    # Fallback: check zip contents
    # If .db file exists, it's likely full sync. If only CSVs, it's delta
    if 'db' in zip_contents:
        logger.info("[v0] Detected FULL DATABASE sync from zip contents (.db file found)")
        return 'full'
    
    if any(key.endswith('.csv') or key not in ['db'] for key in zip_contents.keys()):
        logger.info("[v0] Detected DELTA CHANGES sync from zip contents (CSV files found)")
        return 'delta'
    
    # Default to full sync for safety
    logger.warning("[v0] Could not determine sync type, defaulting to FULL")
    return 'full'

def merge_delta_into_db(dest_db_path, csv_files_dict):
    """
    Merge changes from CSV files into existing local_data.db.
    CSV files contain modified/added rows. Uses UPSERT logic.
    
    :param dest_db_path: Path to existing local_data.db
    :param csv_files_dict: Dict of {table_name: csv_file_path}
    """
    try:
        conn = sqlite3.connect(dest_db_path)
        cursor = conn.cursor()
        
        for table_name, csv_path in csv_files_dict.items():
            if not os.path.exists(csv_path):
                logger.warning(f"[v0] CSV file not found: {csv_path}")
                continue
            
            logger.info(f"[v0] Merging changes for table: {table_name}")
            
            # Read CSV and merge
            import csv
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                
                if not rows:
                    logger.info(f"[v0] No rows in CSV for {table_name}")
                    continue
                
                # Get column names from first row
                columns = list(rows[0].keys())
                cols_str = ','.join([f'"{c}"' for c in columns])
                placeholders = ','.join(['?' for _ in columns])
                
                # UPSERT: INSERT OR REPLACE (assumes primary key is in the table)
                upsert_sql = f'INSERT OR REPLACE INTO "{table_name}" ({cols_str}) VALUES ({placeholders})'
                
                for row in rows:
                    values = tuple(row.get(col) for col in columns)
                    cursor.execute(upsert_sql, values)
                
                conn.commit()
                logger.info(f"[v0] Successfully merged {len(rows)} rows into {table_name}")
                
            except Exception as e:
                logger.error(f"[v0] Error merging CSV for {table_name}: {e}")
                conn.rollback()
        
        conn.close()
        logger.info("[v0] Delta merge completed successfully")
        
    except Exception as e:
        logger.error(f"[v0] Error connecting to DB during merge: {e}")
        raise

def email_contains_zip(msg):
    """Check if email contains a ZIP attachment."""
    logger.info("   Scanning email parts for ZIP...")
    has_zip = False
    
    for part in msg.walk():
        if part.is_multipart():
            continue
        
        filename = part.get_filename()
        content_type = part.get_content_type()
        content_disposition = part.get("Content-Disposition", "")
        
        logger.info(f"    Part: type={content_type}, filename={filename}, disposition={content_disposition[:50] if content_disposition else 'None'}")
        
        if filename and filename.lower().endswith(".zip"):
            logger.info(f"    Found ZIP by filename: {filename}")
            has_zip = True
            
        elif content_type == "application/zip":
            logger.info(f"     Found ZIP by content-type: application/zip")
            has_zip = True
            
        elif content_type == "application/octet-stream" and filename:
            if filename.lower().endswith(".zip"):
                logger.info(f"     Found ZIP in octet-stream: {filename}")
                has_zip = True
                
        elif content_type == "application/octet-stream" or "attachment" in content_disposition.lower():
            try:
                payload = part.get_payload(decode=True)
                if payload and len(payload) > 4:
                    if payload[:2] == b'PK':
                        logger.info(f"     Found ZIP by magic bytes (PK signature)")
                        has_zip = True
            except Exception as e:
                logger.error(f"     Error checking payload: {e}")
    
    return has_zip

# ---------- POP3 + email helpers ----------

def get_latest_mail_with_zip(POP_SERVER, POP_PORT, EMAIL_USER, EMAIL_PASS):
    pop_conn = poplib.POP3_SSL(POP_SERVER, POP_PORT, timeout=30)
    pop_conn.user(EMAIL_USER)
    pop_conn.pass_(EMAIL_PASS)

    resp, items, octets = pop_conn.list()
    total = len(items)
    logger.info(f"Total messages: {total}")

    if total == 0:
        pop_conn.quit()
        return None

    for i in range(total, 0, -1):
        logger.info(f"\nChecking email #{i} ...")

        resp, lines, octets = pop_conn.retr(i)
        raw_message = b"\r\n".join(lines)
        msg = parser.BytesParser(policy=policy.default).parsebytes(raw_message)

        subject = msg.get("Subject", "No Subject")
        from_addr = msg.get("From", "Unknown")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  From: {from_addr}")

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

        logger.debug("DEBUG -> content_type:", content_type, "filename:", filename, "disposition:", disp)

        if filename and filename.lower().endswith(".zip"):
            save_path = os.path.join(save_dir, filename)
            with open(save_path, "wb") as fh:
                fh.write(part.get_payload(decode=True))
            return save_path

        if content_type == "application/zip":
            save_path = os.path.join(save_dir, "backup.zip")
            with open(save_path, "wb") as fh:
                fh.write(part.get_payload(decode=True))
            return save_path

        if content_type == "application/octet-stream":
            if filename:
                save_path = os.path.join(save_dir, filename)
            else:
                save_path = os.path.join(save_dir, "backup.zip")

            with open(save_path, "wb") as fh:
                fh.write(part.get_payload(decode=True))
            return save_path
        
        payload = part.get_payload(decode=True)
        if payload and len(payload) > 4 and payload[:2] == b'PK':
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

def fetch_db_from_latest_email(POP_SERVER, POP_PORT, EMAIL_USER, EMAIL_PASS):
    """
    Enhanced pipeline with hybrid sync support:
    - Detects if sync is FULL DATABASE or DELTA CHANGES
    - For FULL: replaces entire local_data.db
    - For DELTA: merges CSV changes into existing local_data.db
    """
    ensure_folder(TEMP_DIR)
    ensure_folder(DEST_DIR)

    logger.info("[v0] Connecting to POP3 and fetching latest email...")
    msg = get_latest_mail_with_zip(POP_SERVER, POP_PORT, EMAIL_USER, EMAIL_PASS)
    if msg is None:
        logger.info("[v0] No emails found with ZIP attachments.")
        return None

    logger.info("\n[v0] Searching for ZIP attachment...")
    zip_path = extract_zip_from_email(msg, TEMP_DIR)
    if not zip_path:
        logger.info("[v0] No ZIP attachment found in latest email.")
        return None

    logger.info(f"[v0] ZIP downloaded to: {zip_path}")

    logger.info("[v0] Extracting ZIP contents...")
    zip_contents = extract_zip(zip_path, TEMP_DIR)
    
    if not zip_contents:
        logger.error("[v0] No files found inside ZIP.")
        try:
            os.remove(zip_path)
        except:
            pass
        return None

    sync_type = detect_sync_type(msg, zip_contents)
    logger.info(f"[v0] Sync type detected: {sync_type.upper()}")
    
    dest_db_path = os.path.join(DEST_DIR, "local_data.db")
    
    if sync_type == 'full':
        # ===== FULL DATABASE SYNC =====
        logger.info("[v0] Processing FULL DATABASE sync...")
        
        if 'db' not in zip_contents:
            logger.error("[v0] Expected .db file in full sync, but none found.")
            return None
        
        extracted_db = zip_contents['db']
        if not os.path.exists(extracted_db):
            logger.error("[v0] Extracted DB file not found.")
            return None
        
        if not wait_until_file_free(extracted_db, timeout=10):
            logger.warning("[v0] Warning: extracted DB may be locked.")
        
        logger.info("[v0] Cleaning destination folder...")
        clean_destination(DEST_DIR)
        
        logger.info("[v0] Moving full DB to destination...")
        try:
            final_db = move_db(extracted_db, DEST_DIR)
            logger.info(f"[v0] FULL DATABASE installed at: {final_db}")
        except Exception as e:
            logger.error(f"[v0] Failed to move DB: {e}")
            final_db = None
    
    else:
        # ===== DELTA SYNC =====
        logger.info("[v0] Processing DELTA CHANGES sync...")
        
        # Check if local_data.db exists
        if not os.path.exists(dest_db_path):
            logger.error("[v0] No existing local_data.db found for delta sync. Falling back to full sync.")
            if 'db' in zip_contents:
                extracted_db = zip_contents['db']
                clean_destination(DEST_DIR)
                try:
                    final_db = move_db(extracted_db, DEST_DIR)
                    logger.info(f"[v0] Fallback: FULL DATABASE installed at: {final_db}")
                except Exception as e:
                    logger.error(f"[v0] Fallback failed: {e}")
                    final_db = None
            else:
                logger.error("[v0] No full DB or CSV files to use.")
                final_db = None
        else:
            # Extract CSV files and merge
            csv_files = {k: v for k, v in zip_contents.items() if k != 'db'}
            
            if not csv_files:
                logger.warning("[v0] Delta sync but no CSV files found. No changes to merge.")
                final_db = dest_db_path
            else:
                logger.info(f"[v0] Found {len(csv_files)} CSV files to merge...")
                try:
                    merge_delta_into_db(dest_db_path, csv_files)
                    final_db = dest_db_path
                    logger.info("[v0] DELTA changes successfully merged into local DB")
                except Exception as e:
                    logger.error(f"[v0] Failed to merge delta changes: {e}")
                    final_db = None

    # Cleanup
    try:
        os.remove(zip_path)
    except:
        pass

    if final_db:
        logger.info(f"[v0] Final DB path: {final_db}")
    else:
        logger.info("[v0] DB sync failed.")

    return final_db

# ---------- If run as script ----------
# if __name__ == "__main__":
#     result = fetch_db_from_latest_email(...)
#     print("Result:", result)
