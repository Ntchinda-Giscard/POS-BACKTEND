import os
import imaplib
import email
from email import policy
import time
import csv
from sqlalchemy import MetaData, select, update, insert, and_
from session import SessionLocal, engine
from models import POPConfig, FolderConfig


class EmailCSVDownloader:
    def __init__(self, host, user, password, save_dir, target_db_path):
        self.host = host
        self.user = user
        self.password = password
        self.save_dir = save_dir
        self.target_db_path = target_db_path
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)  

    def download_csv_attachments(self):
        """Connects to IMAP server, iterates through messages, and saves CSV attachments."""
        print(f"DEBUG: Attempting to connect to host: '{self.host}'")
        try:
            mail = imaplib.IMAP4_SSL(self.host)
            mail.login(self.user, self.password)
            mail.select('inbox')

            typ, data = mail.search(None, 'ALL')
            if typ != 'OK':
                print("No messages found!")
                return

            msg_ids = data[0].split()
            print(f"DEBUG: Found {len(msg_ids)} messages.")

            for num in msg_ids:
                typ, msg_data = mail.fetch(num, '(RFC822)')
                if typ != 'OK':
                    print(f"Error fetching message {num}")
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email, policy=policy.default)

                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    
                    filename = part.get_filename()
                    if filename and filename.lower().endswith('.csv'):
                        print(f"DEBUG: Found CSV attachment: {filename}")
                        filepath = os.path.join(self.save_dir, filename)
                        
                        # Ensure a unique filename to avoid overwriting
                        counter = 1
                        base, ext = os.path.splitext(filename)
                        while os.path.exists(filepath):
                            filepath = os.path.join(self.save_dir, f"{base}_{counter}{ext}")
                            counter += 1

                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        print(f"DEBUG: Saved {filepath}")
                        
                        # Process the CSV file for database sync
                        self.process_csv(filepath)
            
            mail.close()
            mail.logout()
        except Exception as e:
            print(f"Error during IMAP download: {e}")
            raise e

    def process_csv(self, filepath):
        """
        Reads the CSV file where:
        - First row contains column headers (TABLE_NAME, col1, col2, ...)
        - Subsequent rows contain: table_name, val1, val2, ...
        - All tables use AUUID_0 as the primary key
        - Performs upsert based on AUUID_0
        """
        print(f"DEBUG: Processing CSV {filepath} for database sync...")
        
        # Create engine for the TARGET database (not the config database)
        from sqlalchemy import create_engine
        target_engine = create_engine(f'sqlite:///{self.target_db_path}')
        
        metadata = MetaData()
        try:
            metadata.reflect(bind=target_engine)
            print(f"DEBUG: Available tables in database: {list(metadata.tables.keys())}")
        except Exception as e:
            print(f"Error reflecting database metadata: {e}")
            return

        with target_engine.connect() as conn:
            try:
                with open(filepath, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    
                    # Read header row to get column names
                    header = next(reader, None)
                    if not header:
                        print("Warning: CSV file is empty")
                        return
                    
                    # Header format: TABLE_NAME, col1, col2, col3, ...
                    column_names = [col.strip() for col in header[1:]]  # Skip first column (TABLE_NAME)
                    
                    print(f"DEBUG: CSV columns: {column_names}")
                    
                    for row_idx, row in enumerate(reader, start=2):  # Start at 2 since header is row 1
                        if not row:
                            continue
                        
                        # First column is the table name
                        table_name = row[0].strip()
                        values = row[1:]
                        
                        print(f"DEBUG: Processing table '{table_name}' from row {row_idx}")
                        
                        # Try to find table (case-insensitive)
                        actual_table_name = None
                        for db_table in metadata.tables.keys():
                            if db_table.upper() == table_name.upper():
                                actual_table_name = db_table
                                break
                        
                        if actual_table_name is None:
                            print(f"Warning: Table '{table_name}' not found in database (Row {row_idx}). Available tables: {list(metadata.tables.keys())}. Skipping.")
                            continue
                        
                        table = metadata.tables[actual_table_name]
                        
                        if len(values) != len(column_names):
                            print(f"Warning: Column count mismatch for table '{table_name}'. "
                                  f"CSV has {len(values)} values, Header has {len(column_names)} columns. "
                                  f"(Row {row_idx}). Skipping.")
                            continue
                        
                        # Map values to column names
                        row_data = {}
                        auuid_value = None
                        
                        for i, col_name in enumerate(column_names):
                            val = values[i].strip()
                            
                            # Handle empty strings
                            if val == '':
                                val = None
                            
                            row_data[col_name] = val
                            
                            # Track AUUID_0 value (primary key)
                            if col_name == 'AUUID_0':
                                auuid_value = val
                        
                        if auuid_value is None:
                            print(f"Warning: AUUID_0 not found or is NULL for table '{table_name}' (Row {row_idx}). Skipping.")
                            continue
                        
                        # Check if record exists based on AUUID_0
                        try:
                            if 'AUUID_0' not in table.columns:
                                print(f"Warning: Table '{table_name}' does not have AUUID_0 column (Row {row_idx}). Skipping.")
                                continue
                            
                            pk_column = table.columns['AUUID_0']
                            stmt = select(table).where(pk_column == auuid_value)
                            result = conn.execute(stmt).fetchone()
                            
                            if result:
                                # Update existing record
                                update_stmt = update(table).where(pk_column == auuid_value).values(row_data)
                                conn.execute(update_stmt)
                                print(f"DEBUG: Updated {table_name} record with AUUID_0={auuid_value}")
                            else:
                                # Insert new record
                                insert_stmt = insert(table).values(row_data)
                                conn.execute(insert_stmt)
                                print(f"DEBUG: Inserted {table_name} record with AUUID_0={auuid_value}")
                                
                        except Exception as e:
                            print(f"Error upserting row {row_idx} into '{table_name}': {e}")
                            
                conn.commit()
                print(f"DEBUG: Finished processing {filepath}")
            except Exception as e:
                print(f"Error processing CSV file {filepath}: {e}")


def run_periodic_download(host, user, password, save_dir, target_db_path, interval=60):
    """Periodically instantiates the downloader and fetches CSV attachments."""
    downloader = EmailCSVDownloader(host, user, password, save_dir, target_db_path)
    while True:
        try:
            downloader.download_csv_attachments()
        except Exception as e:
            print(f"Error during scheduled download: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    db = SessionLocal()
    email_config = db.query(POPConfig).first()
    sqlite_db = db.query(FolderConfig).first()
    print(f"Target database path: {sqlite_db.path}")
    print(f"Email config: {email_config}")
    run_periodic_download(
        host=email_config.server,
        user=email_config.username,
        password=email_config.password,
        save_dir="./attachments",
        target_db_path=sqlite_db.path,  # Pass the target database path
        interval=3600  # 1 hour
    )