import sqlite3
from .model import CondFacResponse, Escomte, PayementMode

def get_payment_methode(customer_code: str) -> PayementMode:
    """  """

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT  PTE_0 FROM BPCUSTOMER WHERE BPCNUM_0 = ?", (customer_code, ))

    row = cursor.fetchone()

    return PayementMode(code= row[0])

def get_escomte(customer_code: str) -> Escomte:

    sqlite_conn = sqlite3.connect("sagex3_seed.db")

    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT  DEP_0 FROM BPCUSTOMER WHERE BPCINV_0 = ? ", (customer_code,))

    row = cursor.fetchone()

    return Escomte(code=row[0])

def get_cond_fac(customer_code: str) -> CondFacResponse:

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()

    cursor.execute("SELECT  INVCND_0 FROM BPCUSTOMER WHERE BPCINV_0 = ?", (customer_code,))

    row = cursor.fetchone()

    return CondFacResponse(code=row[0])
