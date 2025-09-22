

import sqlite3
from ..taxe.model import TaxeResponse


def get_regime_taxe(customer_code: str) -> TaxeResponse:
    """Fetch tax regime from the database."""
    # Simulated database fetch
    sqlite3_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite3_conn.cursor() 
    cursor.execute("""
        SELECT
            VACBPR_0
        FROM
            BPCUSTOMER
        WHERE
            BPCNUM_0 = ?
                   """, (customer_code,))
    code = cursor.fetchone()[0]
    cursor.close()
    return TaxeResponse(code=code)