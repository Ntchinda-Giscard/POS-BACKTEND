import imaplib
import email
import os
import zipfile
import shutil


IMAP_SERVER = "imap.gmail.com"     # or your server
EMAIL_USER = "your@email.com"
EMAIL_PASS = "iaju sgdx tatv qwth"



def clean_destination(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

    for f in os.listdir(folder):
        if f.endswith(".db"):
            os.remove(os.path.join(folder, f))

def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
        for name in z.namelist():
            if name.endswith(".db"):
                return os.path.join(extract_to, name)
    return None

def move_db(db_path, destination_folder):
    final_path = os.path.join(destination_folder, os.path.basename(db_path))
    shutil.move(db_path, final_path)
    return final_path
