import sqlite3
from typing import List
from ..addresse.model import AddressInput, AddressRequest

def get_adresse_vente() -> List[AddressRequest]:
    """  """
    result = []
    
    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT FCY_0, FCYNAM_0 FROM FACILITY")
    
    return result
   
    
