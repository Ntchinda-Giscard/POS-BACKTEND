# import poplib
# import ssl

# EMAIL = "ae011site@gmail.com"
# APP_PASSWORD = "xedv bivx zztb pdjm"  # app password
# HOST = "pop.gmail.com"
# PORT = 995

# try:
#     print("Connecting...")
#     server = poplib.POP3_SSL(HOST, PORT, timeout=10)

#     print("Sending USER...")
#     server.user(EMAIL)

#     print("Sending PASS...")
#     server.pass_(APP_PASSWORD)

#     print("Connected successfully!")
#     print("Mailbox status:", server.stat())

#     server.quit()

# except Exception as e:
#     print("POP connection failed:")
#     print(e)


import imaplib

EMAIL = "ae011site@gmail.com"
APP_PASSWORD = "xedvbivxzztbpdjm"

try:
    print("Connecting to Gmail IMAP...")
    imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)

    print("Authenticating...")
    imap.login(EMAIL, APP_PASSWORD)

    print("Connection successful ✅")

    imap.logout()

except Exception as e:
    print("IMAP connection failed ❌")
    print(e)
