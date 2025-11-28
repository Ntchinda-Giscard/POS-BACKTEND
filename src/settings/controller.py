import logging
import sys
from database.session import get_db
from fastapi import APIRouter, Depends
from .model import SettingsInput
from database.models import POPConfig


router = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fastapi.log')
    ]
)

@router.post("/add", response_model=SettingsInput)
async def add_settings(settings: SettingsInput, db=Depends(get_db)):
    logging.debug(f"Received settings to add: {settings}")
    # Here you would add logic to save settings to the database
    db.query(POPConfig).delete()  # Clear existing settings for simplicity
    db.commit()

    new_config = POPConfig(
        server=settings.popServer,
        username=settings.username,
        password=settings.password,
        port=settings.port
    )

    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    db.close()

    return settings
    