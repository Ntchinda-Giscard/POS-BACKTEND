import os
import imaplib
import email
from email import policy
import time
from session import SessionLocal
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
            
            mail.close()
            mail.logout()
        except Exception as e:
            print(f"Error during IMAP download: {e}")
            raise e




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