import sqlite3
from .model import PayementMode

def get_payment_methode(customer_code: str) -> PayementMode:
    """  """

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT  PTE_0 FROM BPCUSTOMER WHERE BPCNUM_0 = ?", (customer_code))

    row = cursor.fetchone()

    return PayementMode(code= row[0])