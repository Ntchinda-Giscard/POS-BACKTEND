

import sqlite3
from typing import List
from unittest import result
from ..taxe.model import AppliedTaxInput, AppliedTaxResponse, TaxeResponse
from database.sync_data import get_db_file
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

def get_regime_taxe(customer_code: str, db: Session) -> TaxeResponse:
    """Fetch tax regime from the database."""
    # Simulated database fetch
    db_path = ""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite_conn.cursor() 
    cursor.execute("""
        SELECT
            VACBPR_0
        FROM
            BPCUSTOMER
        WHERE
            BPCNUM_0 = ?
                   """, (customer_code,))
    row = cursor.fetchone()
    code = row[0] if row else ""
    cursor.close()
    sqlite_conn.close()
    return TaxeResponse(code=code)

def get_niveau_taxe_article(item_code: str, db: Session) -> str:
    """Fetch tax level from the database."""
    # Simulated database fetch
    db_path = ""
    db_path = get_db_file(db)
    sqlite3_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite3_conn.cursor() 
    cursor.execute("""
        SELECT
            VACITM_0
        FROM
            ITMMASTER
        WHERE
            ITMREF_0 = ?
                   """, (item_code,))
    row = cursor.fetchone()
    niveau = row[0] if row else ""
    cursor.close()
    sqlite3_conn.close()
    return niveau

def get_legislation(regime_taxe_tiers: str, db: Session) -> str:
    """Fetch legislation from the database."""
    # Simulated database fetch
    db_path = ""
    db_path = get_db_file(db)
    sqlite3_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite3_conn.cursor() 
    cursor.execute("""
        SELECT
            LEG_0
        FROM
            TABVACBPR
        WHERE
            VACBPR_0 = ?
                   """, (regime_taxe_tiers,))
    legislation = cursor.fetchone()[0]
    cursor.close()
    sqlite3_conn.close()
    return legislation

def get_applied_tax(criterias: List[AppliedTaxInput], db: Session) -> List[AppliedTaxResponse]:
    """Determine the applicable tax per item, the way Sage X3 does it (TABVAC → TABRATVAT)."""
    from .components import DeterminationTaxe
    results = []
    db_path = get_db_file(db)
    sqlite3_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite3_conn.cursor()
    determinateur = DeterminationTaxe(cursor)
    try:
        for criteria in criterias:
            niveau_taxe_article = get_niveau_taxe_article(criteria.item_code, db)
            code_taxe = determinateur.determiner_code_taxe({
                'regime_taxe_tiers': criteria.regime_taxe_tiers,
                'niveau_taxe_article': niveau_taxe_article,
                'site': criteria.site,
                'groupe_societe': criteria.groupe_societe,
                'date': criteria.date,
            })
            if not code_taxe:
                logger.warning(f"Aucun code taxe pour article={criteria.item_code} regime={criteria.regime_taxe_tiers} niveau={niveau_taxe_article}")
                results.append(AppliedTaxResponse(
                    item_code=criteria.item_code, code_taxe="", taux=0.0, exonere=True,
                    warning="Aucune règle de taxe trouvée pour ces critères",
                ))
                continue
            results.append(AppliedTaxResponse(
                item_code=criteria.item_code,
                code_taxe=code_taxe["code_taxe"],
                taux=code_taxe["taux"],
                compte_comptable=code_taxe["compte_comptable"],
                exonere=code_taxe["exonere"],
                regle=code_taxe["regle"],
                legislation=code_taxe["legislation"],
                description=code_taxe["description"],
                warning=code_taxe["warning"],
            ))
    finally:
        cursor.close()
        sqlite3_conn.close()
    return results
