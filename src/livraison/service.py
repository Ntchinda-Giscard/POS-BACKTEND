from unittest import result
from .model import ModeDeLivraisonRequest, TransPorteurResponse
import sqlite3
from typing import List


def get_mode_livraison() -> List[ModeDeLivraisonRequest]:
    results = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT MDL_0 FROM TABMODELIV")

    for row in cursor.fetchall():
        mode = ModeDeLivraisonRequest(
            code=row[0]
        )
        results.append(mode)

    return results

def get_transporteur() -> List[TransPorteurResponse]:
    results = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT BPTNUM_0, BPTNMAM_0 FROM BPCARRIER")

    for row in cursor.fetchall():
        transporteur = TransPorteurResponse(
            code=row[0],
            description=row[1]
        )
        results.append(transporteur)

    return results