import poplib

EMAIL_USER = "giscardntchinda@gmail.com"
EMAIL_PASS = "yzeq tafx waik ihqh"

try:
    pop_conn = poplib.POP3_SSL("pop.gmail.com", 995)
    pop_conn.user(EMAIL_USER)
    pop_conn.pass_(EMAIL_PASS)
    print("LOGIN SUCCESS!")
    pop_conn.quit()
except Exception as e:
    print("LOGIN FAILED →", e)
