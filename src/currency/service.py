import sqlite3
from ..currency.model import CurrencyResponse
from database.sync_data import sync_data_new

def get_commande_currrency(customer_code: str) -> CurrencyResponse:

    db_path = ""
    db_path = sync_data_new()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore

    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT CUR_0 FROM BPCUSTOMER WHERE BPCNUM_0 = ? ", (customer_code,))
    row = cursor.fetchone()
    currency = CurrencyResponse(
            code=row[0],
        )
    
    return currency