import os
import csv
from sqlalchemy import create_engine, MetaData, Column, String, Integer, Table
from get_data_email import EmailCSVDownloader

# Setup a temporary SQLite DB for testing
TEST_DB_FILE = 'test_verification.db'
if os.path.exists(TEST_DB_FILE):
    os.remove(TEST_DB_FILE)

engine = create_engine(f'sqlite:///{TEST_DB_FILE}')
metadata = MetaData()

# Define a test table that matches the CSV structure we expect (partially)
# User's CSV format: TABLE_NAME in first column.
# We will create a table named 'ITMFACILIT' as seen in user's example.
test_table = Table(
    'ITMFACILIT', metadata,
    Column('AUUID_0', String, primary_key=True),
    Column('ITMREF_0', String),
    Column('STOFCY_0', String),
    Column('USE_VAL', String) # Dummy column to check update
)

metadata.create_all(engine)

# Create a Dummy CSV file matching the user's weird format
# Format: 
# Header: TABLE_NAME, col1, col2, ...
# Data:   ActualTableName, val1, val2, ...
CSV_FILE = 'test_data_sync.csv'
with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Header row. Note: FIRST column is strictly 'TABLE_NAME' but corresponds to the table name value in data rows.
    # The OTHER columns are the actual column names in the DB.
    # Based on user's snippet:
    # TABLE_NAME,UPDTICK_0,ITMREF_0,STOFCY_0, ...
    # ITMFACILIT,70,BMS001,AE011, ...
    
    # We'll simulate: TABLE_NAME, AUUID_0, ITMREF_0, STOFCY_0, USE_VAL
    writer.writerow(['TABLE_NAME', 'AUUID_0', 'ITMREF_0', 'STOFCY_0', 'USE_VAL'])
    
    # Row 1: Insert new
    writer.writerow(['ITMFACILIT', 'uuid_1', 'REF001', 'SITE1', 'Initial'])
    
    # Row 2: Update existing (we'll run this logic later or in same file?)
    # For now let's just test single insert.

# We need to monkeypatch the 'engine' imported in get_data_email to use our test engine
import get_data_email
get_data_email.engine = engine

# Instantiate Downloader (args don't matter for process_csv)
downloader = EmailCSVDownloader('host', 'user', 'pass', '.')

print("--- Running process_csv ---")
try:
    downloader.process_csv(CSV_FILE)
except Exception as e:
    print(f"FAILED: {e}")

# Verify Data
from sqlalchemy import select
with engine.connect() as conn:
    result = conn.execute(select(test_table)).fetchall()
    print("\n--- Database Content ---")
    for row in result:
        print(row)

# Cleanup
if os.path.exists(CSV_FILE):
    os.remove(CSV_FILE)
# if os.path.exists(TEST_DB_FILE):
#     os.remove(TEST_DB_FILE)
