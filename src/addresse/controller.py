from typing import List
from src.addresse.service import get_adresse_expedition, get_adresse_livraison, get_adresse_vente
from .model import AddressInput, AddressLivrasonREsponse, AddressRequest
from fastapi import Depends
from sqlalchemy.orm import Session
from database.session import get_db
from fastapi import APIRouter

router = APIRouter(
    prefix="/adresse",
    tags=["adresse"]
)

@router.get("/vente", response_model=List[AddressRequest])
def read_adresse_vente(db: Session = Depends(get_db)):
    return get_adresse_vente(db)

@router.get("/livraison", response_model=List[AddressLivrasonREsponse])
def read_adresse_livraison(code_client: str, db: Session = Depends(get_db)):
    return get_adresse_livraison(code_client, db)

@router.get("/expedition", response_model=List[AddressRequest])
def read_adresse_expedition(legacy_comp: str, db: Session = Depends(get_db)):
    return get_adresse_expedition(legacy_comp, db)