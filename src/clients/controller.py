from typing import List
from src.clients.serivce import get_client_detail, get_client_facture, get_client_orders, get_clients, get_tiers
from .model import ClientDetail, ClientFactureResponse, ClientOrder, ClientResponse, TierResponse
from fastapi import APIRouter, Depends, HTTPException, status
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


@router.get("/{code_client}/detail", response_model=ClientDetail)
def read_client_detail(code_client: str, db: Session = Depends(get_db)):
    """Customer card: identity, terms, address, contact, order and payment totals."""
    detail = get_client_detail(code_client, db)
    if not detail:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client introuvable")
    return detail


@router.get("/{code_client}/orders", response_model=List[ClientOrder])
def read_client_orders(code_client: str, limit: int = 100, db: Session = Depends(get_db)):
    """Purchase history: X3 orders and till orders, with what was paid at the till."""
    return get_client_orders(code_client, db, limit=limit)
