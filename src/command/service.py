import sqlite3
from typing import List
from ..command.model import CommandTypeRRequest

def get_command_types() -> List[CommandTypeRRequest]:
    """Fetch command types from the database."""
    result = []

    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT SOHTYP_0, TSODES_0 FROM TABSOHTYP")

    for row in cursor.fetchall():
        result.append(CommandTypeRRequest(code=row[0], description=row[1]))

    return result
