import logging
from typing import Dict, Optional
from database.session import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from .model import FolderConfigInput, SettingsInput
from .service import get_all_settings, set_settings
from sqlalchemy.orm import Session
from database.models import FolderConfig, POPConfig


router = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)

logger = logging.getLogger(__name__)


@router.post("/add", response_model=SettingsInput)
async def add_settings(settings: SettingsInput, db: Session = Depends(get_db)):
    logger.debug(f"Received settings to add: server={settings.popServer} user={settings.username}")
    # Here you would add logic to save settings to the database
    db.query(POPConfig).delete()  # Clear existing settings for simplicity
    db.commit()

    new_config = POPConfig(
        server=settings.popServer,
        username=settings.username,
        password=settings.password,
        port=settings.port,
        address_vente=settings.addressVente,
        site_livraison=settings.siteLivraison
    )

    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    db.close()

    return settings

@router.get("/get", response_model=Optional[SettingsInput])
async def get_settings(db: Session =Depends(get_db)):
    config = db.query(POPConfig).first()
    if not config:
        return None
    return SettingsInput(
        popServer=config.server,
        username=config.username,
        password=config.password,
        port=config.port,
        addressVente=config.address_vente,
        siteLivraison=config.site_livraison,
    )


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
        logger.error(f"Error saving folder configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str('Une erreur est survenue lors de la sauvegarde de la configuration du dossier.'),
        )


@router.get("/get/folder", response_model=Optional[FolderConfigInput])
async def get_folder_db( db: Session = Depends(get_db)):
    config = db.query(FolderConfig).first()
    if config:
        return FolderConfigInput(
            path=config.path # type: ignore
        )
    return None


@router.get("/app", response_model=Dict[str, str])
def read_app_settings(db: Session = Depends(get_db)):
    """Till settings: low stock threshold, export folder / recipient, SMTP, receipt footer."""
    return get_all_settings(db)


@router.put("/app", response_model=Dict[str, str])
def write_app_settings(values: Dict[str, Optional[str]], db: Session = Depends(get_db)):
    return set_settings(db, values)
