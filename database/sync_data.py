import pyodbc
import sqlite3
from decimal import Decimal
import logging
import os
import zipfile
import shutil
import threading
from database.get_data_email import fetch_db_from_latest_email

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.FileHandler('fastapi.log')
    ]
)
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_FOLDER = r"C:\poswaza\temp"
LOCAL_DB_PATH = rf"{BASE_FOLDER}\db\config.db"
DEST_DIR = rf"C:\poswaza\temp\db"

_sync_lock = threading.Lock()

def get_single_zip(folder):
    files = [f for f in os.listdir(folder) if f.endswith(".zip")]
    return os.path.join(folder, files[0]) if files else None


def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
        for name in z.namelist():
            if name.endswith(".db"):
                return os.path.join(extract_to, name)
    return None


def clean_destination(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

    for f in os.listdir(folder):
        if f.endswith(".db"):
            os.remove(os.path.join(folder, f))


def move_db(db_file, destination_folder):
    dest_file = os.path.join(destination_folder, os.path.basename(db_file))
    shutil.move(db_file, dest_file)
    return dest_file

# def sync_data():
#     # --- Close connections ---
#     sqlserver_conn.close()
#     sqlite_conn.close()
#     print(" All SEED tables copied successfully!")

def sync_data_new():
    with _sync_lock:
        
        

        # if zip_file:
        #     print("ZIP found:", zip_file)

            

            
        try:
            final_db_path = fetch_db_from_latest_email()
            logging.info(f"Fetched DB from email: {final_db_path}")

            return final_db_path
        except Exception as e:
            folder_conn = sqlite3.connect(LOCAL_DB_PATH)
            folder_cursor = folder_conn.cursor()
            folder_cursor.execute("SELECT * FROM configurations_folders")
            folder_rows = folder_cursor.fetchone()
            folder_conn.close()

            source_folder = folder_rows[1]
            destination_folder = folder_rows[2]

            final_db_path = None

            # -----------------------
            # MAIN LOGIC
            # -----------------------

            zip_file = get_single_zip(source_folder)
            logger.error(f"Failed to fetch DB from email: {e}")
            extracted_db = extract_zip(zip_file, source_folder)
            logger.info(f"Extracted DB path: {extracted_db}")
            logger.info(f"Extracted DB: {extracted_db}")
            if extracted_db and os.path.exists(extracted_db):
                logger.error(f"Error moving database: {e}")
                
                # Clean destination (remove old DB)
                clean_destination(destination_folder)

                # Move new DB to destination
                final_db_path = move_db(extracted_db, destination_folder)
                logging.info(f"Extracted DB from folder: {final_db_path}")
                
            return final_db_path


def ensure_folder(folder):
    os.makedirs(folder, exist_ok=True)
    return folder


def get_db_file():
    """
    Scan the folder for a .db file and return its full path.
    Returns None if no .db file is found.
    """
    
   
    db_path = os.path.join(DEST_DIR, "local_data.db")
    if os.path.exists(db_path):
        return db_path
    return None