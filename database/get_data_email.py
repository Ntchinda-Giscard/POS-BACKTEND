import os
import imaplib
import email
from email import policy
import time
import csv
from sqlalchemy import MetaData, select, update, insert, and_
from session import SessionLocal, engine
from models import POPConfig


class EmailCSVDownloader:
    def __init__(self, host, user, password, save_dir):
        self.host = host
        self.user = user
        self.password = password
        self.save_dir = save_dir
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
        Reads the CSV file, identifies the table from the first column of each row,
        and upserts data into the SQLite database.
        """
        print(f"DEBUG: Processing CSV {filepath} for database sync...")
        metadata = MetaData()
        try:
            metadata.reflect(bind=engine)
        except Exception as e:
            print(f"Error reflecting database metadata: {e}")
            return

        with engine.connect() as conn:
            try:
                with open(filepath, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row_idx, row in enumerate(reader):
                        if not row:
                            continue
                        
                        # Assumption: First column is table name
                        table_name = row[0].strip()
                        values = row[1:]
                        
                        if table_name not in metadata.tables:
                            print(f"Warning: Table '{table_name}' not found in database (Row {row_idx+1}). Skipping.")
                            continue
                        
                        table = metadata.tables[table_name]
                        columns = list(table.columns)
                        
                        if len(values) != len(columns):
                            print(f"Warning: Column count mismatch for table '{table_name}'. "
                                  f"CSV has {len(values)} value columns, Table has {len(columns)} columns. "
                                  f"(Row {row_idx+1}). Skipping.")
                            continue
                        
                        # Map values to column names
                        row_data = {}
                        pk_clauses = []
                        
                        for i, col in enumerate(columns):
                            val = values[i]
                            # TODO: Type conversion could be added here if needed
                            row_data[col.name] = val
                            
                            if col.primary_key:
                                pk_clauses.append(col == val)
                        
                        if not pk_clauses:
                            # Table without PK - fallback to Insert only (potential duplicates)
                            try:
                                conn.execute(insert(table).values(row_data))
                            except Exception as e:
                                print(f"Error inserting into '{table_name}': {e}")
                            continue
                        
                        # Check if record exists
                        try:
                            stmt = select(table).where(and_(*pk_clauses))
                            result = conn.execute(stmt).fetchone()
                            
                            if result:
                                # Update
                                update_stmt = update(table).where(and_(*pk_clauses)).values(row_data)
                                conn.execute(update_stmt)
                                print(f"DEBUG: Updated {table_name} record {pk_clauses}")
                            else:
                                # Insert
                                insert_stmt = insert(table).values(row_data)
                                conn.execute(insert_stmt)
                                print(f"DEBUG: Inserted {table_name} record {pk_clauses}")
                                
                        except Exception as e:
                            print(f"Error upserting row {row_idx+1} into '{table_name}': {e}")
                            
                conn.commit()
                print(f"DEBUG: Finished processing {filepath}")
            except Exception as e:
                print(f"Error processing CSV file {filepath}: {e}")




def run_periodic_download(host, user, password, save_dir, interval=3600):
    """Periodically instantiates the downloader and fetches CSV attachments."""
    downloader = EmailCSVDownloader(host, user, password, save_dir)
    while True:
        try:
            downloader.download_csv_attachments()
        except Exception as e:
            print(f"Error during scheduled download: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    db = SessionLocal()
    email_config = db.query(POPConfig).first()
    print(email_config)
    run_periodic_download(
        host=email_config.server,
        user=email_config.username,
        password=email_config.password,
        save_dir="./attachments",
        interval=60  # 1 hour
    )