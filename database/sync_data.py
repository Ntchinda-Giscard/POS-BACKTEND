from fastapi import Depends
from database.models import FolderConfig
from database.session import get_db
import logging
import os
import threading
from sqlalchemy.orm import Session


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.FileHandler('fastapi.log')
    ]
)
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_sync_lock = threading.Lock()

def get_db_file(db: Session) -> str | None:
    """
    Scan the folder for a .db file and return its full path.
    Returns None if no .db file is found.
    """
    
   
    db_config = db.query(FolderConfig).first()
    if db_config:
        db_path = db_config.path  # type: ignore
        logger.info(f"Database path from config: {db_path}")
        print(f"Database path from config: {db_path}")
        if os.path.isfile(db_path) and db_path.endswith('.db'): # type: ignore
            logger.info(f"Database file found: {db_path}")
            return f"{db_path}\\local_data.db" # type: ignore
        else:
            logger.warning(f"The path in the database config is not a valid .db file: {db_path}")
    return None




