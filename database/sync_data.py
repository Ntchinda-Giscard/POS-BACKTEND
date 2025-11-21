import pyodbc
import sqlite3
from decimal import Decimal
import logging
import os
import zipfile
import shutil
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        db_path = r"c:/posdatabase/config.db"
        folder_conn = sqlite3.connect(db_path)
        folder_cursor = folder_conn.cursor()
        folder_cursor.execute("SELECT * FROM configurations_folders")
        folder_rows = folder_cursor.fetchone()
        folder_conn.close()

        source_folder = folder_rows[1]
        destination_folder = folder_rows[2]

        # -----------------------
        # MAIN LOGIC
        # -----------------------

        zip_file = get_single_zip(source_folder)

        if zip_file:
            print("ZIP found:", zip_file)

            extracted_db = extract_zip(zip_file, source_folder)
            logger.info(f"Extracted DB: {extracted_db}")

            if extracted_db and os.path.exists(extracted_db):
                try:
                    # Clean destination (remove old DB)
                    clean_destination(destination_folder)

                    # Move new DB to destination
                    final_db_path = move_db(extracted_db, destination_folder)
                    logging.info(f"Extracted DB: {final_db_path}")

                    # Remove ZIP file from source once processed
                    # os.remove(zip_file)
                    # print("ZIP removed from source:", zip_file)

                    return final_db_path
                except Exception as e:
                    logger.error(f"Error moving database: {e}")
                    return None
            else:
                logger.warning("Extracted DB file not found (possibly moved by another process).")
                return None

        else:
            logger.info("No ZIP file found in source folder.")


import os

def get_db_file():
    """
    Returns the full path of the .db file in the folder.
    If no .db file exists, returns None.
    """
    db_path = r"c:/posdatabase/config.db"
    folder_conn = sqlite3.connect(db_path)
    folder_cursor = folder_conn.cursor()
    folder_cursor.execute("SELECT * FROM configurations_folders")
    folder_rows = folder_cursor.fetchone()
    folder_conn.close()

    source_folder = folder_rows[1]
    destination_folder = folder_rows[2]
    folder_path = destination_folder
    if not os.path.isdir(folder_path):
        return None

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".db"):
            return os.path.join(folder_path, filename)

    return None