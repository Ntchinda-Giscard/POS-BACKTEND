import sqlite3
from typing import List
from ..addresse.model import AddressInput, AddressLivrasonREsponse, AddressRequest
from database.sync_data import get_db_file
def get_adresse_vente() -> List[AddressRequest]:
    """  """
    db_path = ""
    db_path = get_db_file()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    result = []
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT FCY_0, FCYNAM_0, LEGCPY_0 FROM FACILITY ORDER BY FCY_0 ASC")

    for row in cursor.fetchall():
        address = AddressRequest(
            code=row[0],
            description=row[1],
            leg_comp=row[2]
        )
        result.append(address)

    return result


def get_adresse_livraison(code_clinet: str) -> List[AddressLivrasonREsponse]:
    """Fetch delivery addresses from the database."""

    db_path = ""
    db_path = get_db_file()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite_conn.cursor()
    result = []
    cursor.execute("""SELECT BPAADD_0 FROM "BPADDRESS" WHERE "BPANUM_0" = ? """, (code_clinet,))

    for row in cursor.fetchall():
        address = AddressLivrasonREsponse(
            code=row[0]
        )
        result.append(address)

    return result 

def get_adresse_expedition(legacy_comp: str) -> List[AddressRequest]:
    """  """
    
    db_path = ""
    db_path = get_db_file()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    result = []
    cursor = sqlite_conn.cursor()
    cursor.execute("""
                   SELECT
                        FCY_0,
                    FCYNAM_0,
                        LEGCPY_0
                    FROM
                        FACILITY
                    WHERE
                        LEGCPY_0 = ?
                    ORDER BY
                        FCY_0 ASC""", (legacy_comp,))

    for row in cursor.fetchall():
        address = AddressRequest(
            code=row[0],
            description=row[1],
            leg_comp=row[2]
        )
        result.append(address)

    return result

