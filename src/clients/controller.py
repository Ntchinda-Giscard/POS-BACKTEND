from typing import List
from src.clients.serivce import get_client_facture, get_clients, get_tiers
from .model import  ClientFactureResponse, ClientResponse, TierResponse
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/", response_model=List[ClientResponse])
def read_clients(db: Session = Depends(get_db)):
    return get_clients(db)

@router.get("/tiers/", response_model=TierResponse)
def read_tiers(customer_code: str, db: Session = Depends(get_db)):
    return get_tiers(customer_code, db)

@router.get("/facture/", response_model=ClientFactureResponse)
def read_client_facture(code_client: str, db: Session = Depends(get_db)):
    return get_client_facture(code_client, db)