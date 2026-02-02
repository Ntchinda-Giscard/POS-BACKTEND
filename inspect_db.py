import sqlite3
import os

# Assuming database path resolution similar to app
# You might need to adjust the path to your actual .db file
# I'll try to find it relative to current dir or assume a default
DB_PATH = "c:/Users/DIGITAL MARKET/Documents/ProjetWaza/PROJET-POS/POS-ELECTRON/backend/pos.db" 

# If you know the actual path used in get_db_file, usage that.
# Based on existing code: db_path = get_db_file(). 
# But I can't import get_db_file easily without setting up path.
# Let's try to just find a .db file in backend/database or similar.

def inspect_table(table_name):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"Schema for {table_name}:")
        for col in columns:
            print(col)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_table("SDELIVERY")
    print("-" * 20)
    inspect_table("SDELIVERYD")
