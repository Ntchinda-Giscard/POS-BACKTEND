import sqlite3
from typing import List
from unittest import result
from ..clients.model import ClientLivreResponse, ClientResponse, TierResponse

def get_clients() -> List[ClientResponse]:
    """Fetch clients from the database."""
    result = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT BPCNUM_0, BPCNAM_0, CUR_0 FROM BPCUSTOMER")

    for row in cursor.fetchall():
        client = ClientResponse(
            code=row[0],
            name=row[1],
            cur=row[2]
        )
        result.append(client)

    return result


def get_tiers(customer_code: str) -> TierResponse:
    """" Get tiers """
    result = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute(("""SELECT "BPCPYR_0", "BPCNAM_0" FROM BPARTNER 
    JOIN BPCUSTOMER
    ON BPCUSTOMER.BPCNUM_0 = BPARTNER.BPRNUM_0
    WHERE BPCUSTOMER.BPCNUM_0  = ? """), (customer_code,))

    row = cursor.fetchone()
    tier = TierResponse(
            code=row[0],
            name=row[1]
        )

    return tier

def get_client_livre():
    """Fetch clients from the database."""
    result = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT BPCNUM_0 FROM BPDLVCUST")

    for row in cursor.fetchall():
        client = ClientLivreResponse(
            code=row[0],
        )
        result.append(client)

    return result