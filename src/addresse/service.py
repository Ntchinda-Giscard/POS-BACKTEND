import sqlite3
from typing import List
from ..addresse.model import AddressInput, AddressLivrasonREsponse, AddressRequest

def get_adresse_vente() -> List[AddressRequest]:
    """  """
    result = []
    
    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT FCY_0, FCYNAM_0 FROM FACILITY")

    for row in cursor.fetchall():
        address = AddressRequest(
            code=row[0],
            description=row[1]
        )
        result.append(address)

    return result


def get_adresse_livraison(code_clinet: str) -> List[AddressLivrasonREsponse]:
    """Fetch delivery addresses from the database."""
    result = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("""SELECT "BPAADD_0" FROM "BPCUSTOMER"
WHERE "BPCNUM_0" = ? """, (code_clinet,))

    for row in cursor.fetchall():
        address = AddressLivrasonREsponse(
            code=row[0]
        )
        result.append(address)

    return result 



