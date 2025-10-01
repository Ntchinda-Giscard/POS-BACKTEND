import pyodbc
import sqlite3
from decimal import Decimal


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
    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    sqlite_cursor = sqlite_conn.cursor()

    # --- 3. SEED schema tables to copy ---
    # All tables use AUUID_0 as the primary key
    tables = [
        "ITMMASTER", "ITMSALES", "ITMFACILIT", "BPARTNER", "BPCUSTOMER",
        "BPCUSTMVT", "BPDLVCUST", "SALESREP", "SPRICLINK", "PRICSTRUCT",
        "SPREASON", "SPRICCONF", "SPRICLIST", "SORDER", "PIMPL",
        "TABMODELIV", "STOCK", "FACILITY", "BPCARRIER", "COMPANY",
        "TABSOHTYP", "TABVACBPR", "SVCRVAT", "ITMCATEG", "CBLOB",
        "BLOBEXPENSES", "ABLOB", "AUTILIS", "AMENUSER", "TABVAT",
        "BPADDRESS", "WAREHOUSE", "TABPAYTERM", "TABDEPAGIO", "BPCINVVAT",
        "TABRATVAT", "TABVACITM", "TABVAC", "TAXLINK", "SFOOTINV",
        "SORDERQ", "SORDERP"
    ]
    
    primary_key = "AUUID_0"  # Universal primary key for all tables

    for table in tables:
        print(f" Processing table: SEED.{table}")

        # --- Get column info from SQL Server ---
        sqlserver_cursor.execute(f"SELECT TOP 0 * FROM SEED.{table}")
        columns = [col[0] for col in sqlserver_cursor.description]
        
        # Verify AUUID_0 exists in the table
        if primary_key not in columns:
            print(f"   WARNING: {primary_key} not found in {table}, skipping...")
            continue

        # --- Check if table exists in SQLite ---
        sqlite_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        table_exists = sqlite_cursor.fetchone() is not None

        if not table_exists:
            # Create table with PRIMARY KEY constraint on AUUID_0
            col_defs = []
            for c in columns:
                if c == primary_key:
                    col_defs.append(f'"{c}" TEXT PRIMARY KEY')
                else:
                    col_defs.append(f'"{c}" TEXT')
            
            create_sql = f"CREATE TABLE {table} ({', '.join(col_defs)})"
            sqlite_cursor.execute(create_sql)
            print(f"  Created table with primary key: {primary_key}")

        # --- Fetch all rows from SQL Server ---
        sqlserver_cursor.execute(f"SELECT * FROM SEED.{table}")
        rows = sqlserver_cursor.fetchall()

        # --- Convert Decimal to float for SQLite ---
        def convert_row(row):
            return [float(x) if isinstance(x, Decimal) else x for x in row]

        converted_rows = [convert_row(r) for r in rows]

        # --- Use INSERT OR REPLACE to merge data ---
        placeholders = ", ".join(["?"] * len(columns))
        insert_sql = f"INSERT OR REPLACE INTO {table} VALUES ({placeholders})"
        
        sqlite_cursor.executemany(insert_sql, converted_rows)
        sqlite_conn.commit()

        print(f"  {table}: {len(rows)} rows synced (upsert based on PK).")

    # --- Close connections ---
    sqlserver_conn.close()
    sqlite_conn.close()
    print("\n All SEED tables synced successfully!")


if __name__ == "__main__":
    sync_data()