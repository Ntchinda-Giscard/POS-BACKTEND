import sqlite3
from typing import List
from ..command.model import CommandTypeRRequest, CreateCommandRequest
import uuid
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
def get_command_types(db: Session = None) -> List[CommandTypeRRequest]:
    """Fetch command types from the database."""

    db_path = ""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    result = []
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT SOHTYP_0, TSODES_0 FROM TABSOHTYP")

    for row in cursor.fetchall():
        logger.debug(f"Fetched command type row: {row}")
        result.append(CommandTypeRRequest(code=row[0], description=row[1]))
    sqlite_conn.close()
    return result

def create_commande(inputs: CreateCommandRequest, db: Session):
    """Create a new command in the database."""
    sorder_auuid = uuid.uuid4()
    sorder_binary_id = sorder_auuid.bytes
    
    query_create_sorder = """
            INSERT INTO
        SORDER (
            AUUID_0, -- uuid
            SOHNUM_0, -- order number
            VACBPR_0, -- regime taxe
            SOHTYP_0, -- order type
            SALFCY_0, -- site de vente
            BPCORD_0, -- order client
            BPCINV_0, -- invoice client
            BPCPYR_0, -- payer client
            CUR_0, -- currency
            ORDNOT_0, -- total ligne ht prix
            ORDATI_0, -- total ligne ttc prix
            ORDINVNOT_0, -- valorisation Ht
            ORDINVATI_0, -- valorisation TTC
            PRITYP_0 -- price type
        )
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    query_create_sorderp = """
            INSERT INTO SORDERP(
                AUUID_0,
                SOHNUM_0,
                GROPRI_0,
                NETPRINOT_0,
                NETPRIATI_0,
                FOCFLG_0,
                ITMREF_0
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?)
        """

    query_create_sorderq = """
            INSERT INTO SORDERQ(
                AUUID_0,
                SOHNUM_0,
                ITMREF_0,
                QTY_0,
                ALLQTY_0
            )
            VALUES
            (?, ?, ?, ?, ?)
        """
    
    db_path = ""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite_conn.cursor()

    # sohnnum = str(uuid.uuid4())[:8]  # Generate a unique order number
    sohnnum = inputs.num_comd

    sorder_out = cursor.execute( query_create_sorder,(
        sorder_binary_id,
        sohnnum,
        inputs.regime_taxe,
        inputs.comd_type,
        inputs.site_vente,
        inputs.client_comd,
        inputs.client_facture,
        inputs.client_payeur,
        inputs.currency,
        inputs.total_ht,
        inputs.total_ttc,
        inputs.valo_ht,
        inputs.valo_ttc,
        inputs.price_type
    ))

    for line in inputs.ligne:
        sorderp_auuid = uuid.uuid4()
        sorderp_binary_id = sorderp_auuid.bytes
        sorderq_auuid = uuid.uuid4()
        sorderq_binary_id = sorderq_auuid.bytes
        focflg_value = 1 if (line.free_items is not None and len(line.free_items) > 0) else 0


        sorderp_out = cursor.execute( query_create_sorderp,(
            sorderp_binary_id,
            sohnnum,
            line.prix_brut,
            line.prix_net_ht,
            line.prix_net_ttc,
            focflg_value,
            line.item_code
        ))

        sorderq_out = cursor.execute( query_create_sorderq,(
            sorderp_binary_id,
            sohnnum,
            line.item_code,
            line.quantity,
            line.quantity
        ))
        logger.debug(f"Inserted line item: {line.item_code} with quantity {line.quantity}")
    
    sqlite_conn.commit()
    sqlite_conn.close()
    return { 'sorder': sohnnum }

def get_commnde_livrison(db: Session):
    """
        Get all sorders that are linked to the sdelivery table
    """
    db_path = ""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT BPCINV_0, SOHNUM_0, BPCORD_0 FROM SORDER WHERE SOHNUM_0 IN (SELECT SOHNUM_0 FROM SDELIVERY)")
    result = cursor.fetchall()
    sqlite_conn.close()
    return result