from .model import ModeDeLivraisonRequest, TransPorteurResponse
import sqlite3
from typing import List
from database.sync_data import get_db_file
import logging
import sys
from sqlalchemy.orm import Session


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)

logger = logging.getLogger(__name__)

def get_mode_livraison() -> List[ModeDeLivraisonRequest]:

    db_path = ""
    db_path = get_db_file()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore

    results = []
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT MDL_0 FROM TABMODELIV")

    for row in cursor.fetchall():
        logger.debug(f"Fetched mode livraison row: {row}")
        mode = ModeDeLivraisonRequest(
            code=row[0]
        )
        results.append(mode)
    sqlite_conn.close()
    return results

def get_transporteur() -> List[TransPorteurResponse]:

    db_path = ""
    db_path = get_db_file()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    results = []
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT BPTNUM_0, BPTNAM_0 FROM BPCARRIER")

    for row in cursor.fetchall():
        logger.debug(f"Fetched transporteur row: {row}")
        transporteur = TransPorteurResponse(
            code=row[0],
            description=row[1]
        )
        results.append(transporteur)
    sqlite_conn.close()
    return results


def get_livraison(db: Session):

    db_path = ""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    results = []
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT SHIDAT_0, DLVDAT_0, BPDNAM_0, SOHNUM_0 FROM SDELIVERY")

    for row in cursor.fetchall():
        logger.debug(f"Fetched livraison row: {row}")
        livraison = {
            'code': row[0],
            'date_expedition': row[1],
            'client_livre': row[2],
            'commande_livre': row[3]
        }
        results.append(livraison)
    sqlite_conn.close()
    logger.debug(f"Fetched livraison rows: {results}")
    return results
    