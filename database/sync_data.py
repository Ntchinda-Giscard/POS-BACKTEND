import pyodbc
import sqlite3
from decimal import Decimal

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
sqlite_conn = sqlite3.connect("sagex3_seed.db")
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
    "TABVACBPR",
    "BPCINVVAT",
    "TABVAT",
    "TABRATVAT",
    "TABVACITM",
    "TABVAC",
    "TAXLINK"
]

for table in tables:
    print(f"📂 Processing table: SEED.{table}")

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

    print(f"✅ {table}: {len(rows)} rows copied.")

# --- Close connections ---
sqlserver_conn.close()
sqlite_conn.close()
print("🎉 All SEED tables copied successfully!")


