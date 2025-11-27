import sqlite3
from ..currency.model import CurrencyResponse
from database.sync_data import get_db_file

def get_commande_currrency(customer_code: str) -> CurrencyResponse:

    db_path = ""
    db_path = get_db_file()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore

    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT CUR_0 FROM BPCUSTOMER WHERE BPCNUM_0 = ? ", (customer_code,))
    row = cursor.fetchone()
    currency = CurrencyResponse(
            code=row[0],
        )
    sqlite_conn.close()
    
    return currency