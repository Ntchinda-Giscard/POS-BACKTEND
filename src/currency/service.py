import sqlite3
from ..currency.model import CurrencyResponse

def get_commande_currrency(customer_code: str) -> CurrencyResponse:

    sqlite_conn = sqlite3.connect("sagex3_seed.db")

    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT CUR_0 FROM BPCUSTOMER WHERE BPCNUM_0 = ? ", (customer_code,))
    row = cursor.fetchone()
    currency = CurrencyResponse(
            code=row[0],
        )
    
    return currency