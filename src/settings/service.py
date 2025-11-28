import logging
import sys
from database.session import get_db

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)


