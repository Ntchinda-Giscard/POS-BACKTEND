

import sqlite3
from ..taxe.model import AppliedTaxInput, AppliedTaxResponse, TaxeResponse


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

def get_applied_tax(criteria: AppliedTaxInput) -> AppliedTaxResponse:
    """Determine the applicable tax based on criteria."""
    from .components import DeterminationTaxe

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    determinateur = DeterminationTaxe(cursor)
    code_taxe = determinateur.determiner_code_taxe({
        'regime_taxe_tiers':  criteria.regime_taxe_tiers,
        'niveau_taxe_article': criteria.niveau_taxe_article,
        'legislation': criteria.legislation,
        'groupe_societe': criteria.groupe_societe
    })
    if not code_taxe:
        raise Exception("Aucun code taxe trouvé pour ces critères")

    details_taxe = determinateur._recuperer_details_taxe(code_taxe)
    cursor.close()
    if not details_taxe:
        raise Exception(f"Aucun détail trouvé pour le code taxe {code_taxe}")

    return AppliedTaxResponse(
        code_taxe=code_taxe.get('code_taxe', ''),
        taux= code_taxe.get('taux', 0.0) if code_taxe.get('taux', 0.0) else 0.0, # type: ignore
    )