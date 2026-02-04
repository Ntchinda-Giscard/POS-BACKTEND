import sqlite3

db_path = r"E:\DB\local_data.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(SDELIVERYD)")
    columns = cursor.fetchall()
    print(f"Schema for SDELIVERYD in {db_path}:")
    for col in columns:
        print(col)
    conn.close()
except Exception as e:
    print(f"Error accessing DB: {e}")
