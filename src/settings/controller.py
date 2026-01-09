import logging
import sys
from database.session import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from .model import FolderConfigInput, SettingsInput
from sqlalchemy.orm import Session
from database.models import FolderConfig, POPConfig


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
async def add_settings(settings: SettingsInput, db: Session = Depends(get_db)):
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

@router.get("/get", response_model=SettingsInput)
async def get_settings(db: Session =Depends(get_db)):
    config = db.query(POPConfig).first()
    if config:
        return SettingsInput(
            popServer=config.server, # type: ignore
            username=config.username, # type: ignore
            password=config.password, # type: ignore
            port=config.port, # type: ignore
        )
    return None


@router.post("/add/folder", response_model=FolderConfigInput)
async def add_folder_db( add_config: FolderConfigInput, db: Session = Depends(get_db)):
    config = db.query(FolderConfig).delete()

    folder_config = FolderConfig(
        path=add_config.path
    )

    try:
        db.add(folder_config)
        db.commit()
        db.refresh(folder_config)
        return add_config
    except Exception as e:
        logging.error(f"Error saving folder configuration: {e}")
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str('Une erreur est survenue lors de la sauvegarde de la configuration du dossier.'),
        )


@router.get("/get/folder", response_model=FolderConfigInput)
async def get_folder_db( db: Session = Depends(get_db)):
    config = db.query(FolderConfig).first()
    if config:
        return FolderConfigInput(
            path=config.path # type: ignore
        )
    return None