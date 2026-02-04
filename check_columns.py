import sqlite3

db_path = r"E:\DB\local_data.db"
required_columns = ["QTY_0", "SHIDAT_0", "SDDLIN_0", "STOFCY_0", "SOHNUM_0", "SDHNUM_0", "ITMREF_0"]

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(SDELIVERYD)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print(f"Checking columns in SDELIVERYD:")
    for req in required_columns:
        exists = req in columns
        print(f"{req}: {'EXISTS' if exists else 'MISSING'}")
        
    conn.close()
except Exception as e:
    print(f"Error accessing DB: {e}")
