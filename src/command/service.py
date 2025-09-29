import sqlite3
from typing import List
from ..command.model import CommandTypeRRequest, CreateCommandRequest
import uuid

def get_command_types() -> List[CommandTypeRRequest]:
    """Fetch command types from the database."""
    result = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT SOHTYP_0, TSODES_0 FROM TABSOHTYP")

    for row in cursor.fetchall():
        result.append(CommandTypeRRequest(code=row[0], description=row[1]))

    return result

def create_commande(input: CreateCommandRequest):
    """Create a new command in the database."""
    sorder_auuid = uuid.uuid4()
    sorder_binary_id = sorder_auuid.bytes
    
    query_create_sorder = """
            INSERT INTO
        SORDER (
            AUUID_0, -- uuid
            SOHNUM_0, -- order number
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
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    query_create_sorderp = """
            INSERT INTO SORDERP(
                AUUID_0,
                SOHNUM_0,
                GROPRI_0,
                NETPRINOT_0,
                NETPRINATI_0,
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
                ALLQTY_0,
            )
            VALUES
            (?, ?, ?, ?, ?)
        """
    
    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()

    sohnnum = str(uuid.uuid4())[:8]  # Generate a unique order number

    sorder_out = cursor.execute( query_create_sorder,(
        sorder_binary_id,
        sohnnum,
        input.comd_type,
        input.site_vente,
        input.client_comd,
        input.client_facture,
        input.client_payeur,
        input.currency,
        input.total_ht,
        input.total_ttc,
        input.valo_ht,
        input.valo_ttc,
        input.price_type
    ))

    for line in input.ligne:
        sorderp_auuid = uuid.uuid4()
        sorderq_auuid = uuid.uuid4()
        sorderp_out = cursor.execute( query_create_sorderp,(
            sorder_binary_id,
            sohnnum,
            line.item_code,
            line.prix_net_ht,
            line.prix_net_ttc,
            0,  # Assuming FOCFLG_0 is 0 for simplicity
            line.item_code
        ))

        sorderq_out = cursor.execute( query_create_sorderq,(
            sorder_binary_id,
            sohnnum,
            line.item_code,
            1,  # Assuming QTY_0 is 1 for simplicity
            1   # Assuming ALLQTY_0 is 1 for simplicity
        ))


