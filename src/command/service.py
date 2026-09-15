import logging
import sqlite3
import uuid
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from database.sync_data import get_db_file
from ..command.model import CommandTypeRRequest, CreateCommandRequest

logger = logging.getLogger(__name__)


def get_command_types(db: Session = None) -> List[CommandTypeRRequest]:
    """Fetch command types from the database."""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    result = []
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT SOHTYP_0, TSODES_0 FROM TABSOHTYP")

    for row in cursor.fetchall():
        result.append(CommandTypeRRequest(code=row[0], description=row[1]))
    sqlite_conn.close()
    return result


def create_commande(inputs: CreateCommandRequest, db: Session):
    """
    Write a sales order the way Sage X3 stores it: SORDER header, one SORDERP (price) and one
    SORDERQ (quantity) row per line, line numbers in steps of 1000. Rows created here have no
    ZTRANSFERT_0 value, which is how the export to X3 finds them later.
    """
    now = datetime.now()
    order_date = (inputs.order_date or now.strftime("%Y-%m-%d"))[:10] + " 00:00:00"
    stock_site = inputs.site_stock or inputs.site_vente
    user = inputs.user_code or "POS"

    query_create_sorder = """
        INSERT INTO SORDER (
            AUUID_0, SOHNUM_0, VACBPR_0, SOHTYP_0, SALFCY_0, STOFCY_0,
            BPCORD_0, BPCINV_0, BPCPYR_0, CUR_0,
            ORDNOT_0, ORDATI_0, ORDINVNOT_0, ORDINVATI_0, PRITYP_0,
            ORDDAT_0, ORDSTA_0, CREUSR_0, CREDAT_0, CREDATTIM_0, UPDUSR_0, UPDDAT_0
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    query_create_sorderp = """
        INSERT INTO SORDERP (
            AUUID_0, SOHNUM_0, SOPLIN_0, ITMREF_0, ITMDES_0, SAU_0,
            GROPRI_0, NETPRI_0, NETPRINOT_0, NETPRIATI_0, VAT_0, FOCFLG_0, CREUSR_0
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    query_create_sorderq = """
        INSERT INTO SORDERQ (
            AUUID_0, SOHNUM_0, SOPLIN_0, SOQSEQ_0, ITMREF_0, STOFCY_0, QTY_0, ORIQTY_0, ALLQTY_0, QTYSTU_0
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    cursor = sqlite_conn.cursor()
    sohnnum = inputs.num_comd

    try:
        cursor.execute(query_create_sorder, (
            uuid.uuid4().bytes,
            sohnnum,
            inputs.regime_taxe,
            inputs.comd_type,
            inputs.site_vente,
            stock_site,
            inputs.client_comd,
            inputs.client_facture,
            inputs.client_payeur,
            inputs.currency,
            inputs.total_ht,
            inputs.total_ttc,
            inputs.valo_ht,
            inputs.valo_ttc,
            inputs.price_type,
            order_date,
            "1",                      # ORDSTA_0: 1 = open
            user,
            now.strftime("%Y-%m-%d 00:00:00"),
            now.strftime("%Y-%m-%d %H:%M:%S"),
            user,
            now.strftime("%Y-%m-%d 00:00:00"),
        ))

        for index, line in enumerate(inputs.ligne, start=1):
            line_number = index * 1000
            description = line.description
            unit = line.unit
            if not description or not unit:
                item = cursor.execute(
                    "SELECT ITMDES1_0, COALESCE(NULLIF(TRIM(SAU_0), ''), STU_0) FROM ITMMASTER WHERE ITMREF_0 = ?",
                    (line.item_code,),
                ).fetchone()
                if item:
                    description = description or (item[0] or "").strip()
                    unit = unit or (item[1] or "").strip()
            focflg_value = 1 if (line.free_items is not None and len(line.free_items) > 0) else 0

            cursor.execute(query_create_sorderp, (
                uuid.uuid4().bytes, sohnnum, line_number, line.item_code, description or "", unit or "",
                line.prix_brut if line.prix_brut is not None else line.prix_net_ht,
                line.prix_net_ht, line.prix_net_ht, line.prix_net_ttc,
                line.tax_code or "", focflg_value, user,
            ))
            cursor.execute(query_create_sorderq, (
                uuid.uuid4().bytes, sohnnum, line_number, line_number, line.item_code, stock_site,
                line.quantity, line.quantity, line.quantity, line.quantity,
            ))

        sqlite_conn.commit()
    except Exception:
        sqlite_conn.rollback()
        raise
    finally:
        sqlite_conn.close()

    logger.info(f"Created order {sohnnum} ({len(inputs.ligne)} lines) by {user}")
    return {'sorder': sohnnum}
