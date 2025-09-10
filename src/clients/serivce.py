import sqlite3
from typing import List
from unittest import result
from ..clients.model import ClientFactureResponse, ClientResponse, TierResponse

def get_clients() -> List[ClientResponse]:
    """Fetch clients from the database."""
    result = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("""
SELECT
  BPCNUM_0,
  BPCNAM_0,
  CUR_0,
  IME_0
FROM
  BPCUSTOMER
ORDER BY
  BPCNUM_0 ASC""")

    for row in cursor.fetchall():
        client = ClientResponse(
            code=row[0],
            name=row[1],
            cur=row[2],
            mode_fac=row[3]
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

def get_client_facture(code_client: str) -> ClientFactureResponse:
    """Fetch clients from the database."""

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT BPCINV_0 FROM BPCUSTOMER WHERE BPCNUM_0 = ? ", ("C0001",))

    row = cursor.fetchone()
    clientFacture = ClientFactureResponse(
            code=row[0]
        )
        

    return clientFacture