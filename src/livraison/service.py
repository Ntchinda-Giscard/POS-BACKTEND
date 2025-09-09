from unittest import result
from .model import ModeDeLivraisonRequest
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