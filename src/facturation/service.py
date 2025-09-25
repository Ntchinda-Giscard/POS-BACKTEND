import sqlite3
from .model import CondFacResponse, Escomte, PayementMode, ElementFacturation
from typing import List

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

def get_element_facturation(customer_code: str) -> List[ElementFacturation]:

    result = []
    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    for i in range(30):
        query = f"""
        SELECT T1.INVDTA_{i}, T1.INVDTAAMT_{i}, T2.VALTYP_0, T2.INCDCR_0, T2.LANDESSHO_0
        FROM BPCUSTOMER AS T1
        JOIN SFOOTINV AS T2 ON T1.INVDTA_{i} = T2.SFINUM_0
        WHERE BPCNUM_0 = ?
        """

        print(f"Exécution de la requête pour l'élément de facturation {i} avec query={query}")
        cursor.execute(query, (customer_code,))
        row = cursor.fetchone()
        print(f"Résultat de la requête pour l'élément de facturation {i}: {row}")
        if row and row[0]:
            result.append(ElementFacturation(code=row[0], amount=row[1], type=row[2], majmin=row[3], description=row[4]))
    cursor.close()
    sqlite_conn.close()
    return result