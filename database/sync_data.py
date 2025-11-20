import pyodbc
import sqlite3
from decimal import Decimal
import logging
import os
import zipfile
import shutil


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_single_zip(folder):
    """Return the only ZIP file in the folder, or None."""
    files = [f for f in os.listdir(folder) if f.endswith(".zip")]
    return os.path.join(folder, files[0]) if files else None


def extract_zip(zip_path, extract_to):
    """Extract ZIP and return the extracted DB file path."""
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
        for name in z.namelist():
            if name.endswith(".db"):
                return os.path.join(extract_to, name)
    return None


def clean_destination(folder):
    """Remove all .db files in the destination folder."""
    if not os.path.exists(folder):
        os.makedirs(folder)

    for f in os.listdir(folder):
        if f.endswith(".db"):
            os.remove(os.path.join(folder, f))


def move_db(db_file, destination_folder):
    """Move DB file to destination."""
    dest_file = os.path.join(destination_folder, os.path.basename(db_file))
    shutil.move(db_file, dest_file)
    return dest_file

def sync_data():
    # --- 1. Connect to SQL Server ---
    sqlserver_conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=192.168.2.41,1433;"
        "DATABASE=x3waza;"
        "UID=superadmin;"
        "PWD=MotDePasseFort123!;"
    )
    sqlserver_cursor = sqlserver_conn.cursor()

    # --- 2. Connect to SQLite ---
    sqlite_conn = sqlite3.connect("sagex3_seed.db", timeout=30, check_same_thread=False)
    sqlite_cursor = sqlite_conn.cursor()

    # --- 3. SEED schema tables to copy ---
    tables = [
        "ITMMASTER",
        "ITMSALES",
        "ITMFACILIT",
        "BPARTNER",
        "BPCUSTOMER",
        "BPCUSTMVT",
        "BPDLVCUST",
        "SALESREP",
        "SPRICLINK",
        "PRICSTRUCT",
        "SPREASON",
        "SPRICCONF",
        "SPRICLIST",
        "SORDER",
        "PIMPL",
        "TABMODELIV",
        "STOCK",
        "FACILITY",
        "SORDER",
        "BPCARRIER",
        "COMPANY",
        "BPDLVCUST",
        "TABSOHTYP",
        "TABVACBPR",
        "SVCRVAT",
        "ITMCATEG",
        "CBLOB",
        "BLOBEXPENSES",
        "ABLOB",
        "AUTILIS",
        "AMENUSER",
        "TABVAT",
        "BPADDRESS",
        "WAREHOUSE",
        "TABMODELIV",
        "TABPAYTERM",
        "TABDEPAGIO",
        "BPCINVVAT",
        "TABVAT",
        "TABRATVAT",
        "TABVACITM",
        "TABVAC",
        "TAXLINK",
        "SFOOTINV",
        "SORDERQ",
        "SORDERP"
    ]



    for table in tables:
        print(f" Processing table: SEED.{table}")

        # --- Get column names ---
        sqlserver_cursor.execute(f"SELECT TOP 0 * FROM SEED.{table}")
        columns = [col[0] for col in sqlserver_cursor.description]

        # --- Drop + create SQLite table ---
        col_defs = ", ".join([f'"{c}" TEXT' for c in columns])
        sqlite_cursor.execute(f"DROP TABLE IF EXISTS {table}")
        sqlite_cursor.execute(f"CREATE TABLE {table} ({col_defs})")

        # --- Fetch all rows from SQL Server ---
        sqlserver_cursor.execute(f"SELECT * FROM SEED.{table}")
        rows = sqlserver_cursor.fetchall()

        # --- Convert Decimal to float/str for SQLite ---
        def convert_row(row):
            return [float(x) if isinstance(x, Decimal) else x for x in row]

        converted_rows = [convert_row(r) for r in rows]

        # --- Insert into SQLite ---
        placeholders = ", ".join(["?"] * len(columns))
        insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"
        sqlite_cursor.executemany(insert_sql, converted_rows)
        sqlite_conn.commit()

        print(f" {table}: {len(rows)} rows copied.")

    # --- Close connections ---
    sqlserver_conn.close()
    sqlite_conn.close()
    print(" All SEED tables copied successfully!")

def sync_data_new():
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
        print("Extracted DB:", extracted_db)

        # Clean destination (remove old DB)
        clean_destination(destination_folder)

        # Move new DB to destination
        final_db_path = move_db(extracted_db, destination_folder)
        print("New DB installed at:", final_db_path)

        # Remove ZIP file from source once processed
        os.remove(zip_file)
        print("ZIP removed from source:", zip_file)

    else:
        print("No ZIP file found in source folder.")

if __name__ == "__main__":
    sync_data()


