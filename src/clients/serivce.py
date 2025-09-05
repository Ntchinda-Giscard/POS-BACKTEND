import sqlite3
from typing import List
from ..clients.model import ClientResponse

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
