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
            AUUID_0,
            SOHNUM_0,
            SOHTYP_0,
            SALFCY_0,
            BPCORD_0,
            BPCINV_0,
            BPCPYR_0,
            CUR_0,
            ORDNOT_0,
            ORDATI_0,
            ORDINVNOT_0,
            ORDINVATI_0,
            PRITYP_0
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