from fastapi import APIRouter, Depends
from .model import (
    ModeDeLivraisonRequest, 
    TransPorteurResponse, 
    LivraisonType, 
    CommandeLivraison,
    CommandeQuantite
)
from .service import ( 
    get_mode_livraison, 
    get_transporteur, 
    get_livraison, 
    get_livraison_type, 
    get_commnde_livrison,
    get_commant_quantite
)
from database.session import get_db
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/livraison",
    tags=["Livraison"]
)

@router.get("/modelivraison", response_model=list[ModeDeLivraisonRequest])
def read_mode_livraison():
    return get_mode_livraison()

@router.get("/transporteur", response_model=list[TransPorteurResponse])
def read_transporteur():
    return get_transporteur()


@router.get("/all")
def read_livraison( db: Session = Depends(get_db)):
    return get_livraison(db)

@router.get("/type", response_model=list[LivraisonType])
def read_livraison_type(db: Session = Depends(get_db)):
    return get_livraison_type(db)


@router.get("/commande", response_model=list[CommandeLivraison])
def read_commande(db: Session = Depends(get_db)):
    return get_commnde_livrison(db)

@router.get("/commande/quantite", response_model=list[CommandeQuantite])
def read_commande_quantite(db: Session = Depends(get_db)):
    return get_commant_quantite(db)


