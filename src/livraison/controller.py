from fastapi import APIRouter
from .model import ModeDeLivraisonRequest, TransPorteurResponse
from .service import get_mode_livraison, get_transporteur, get_livraison


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


@router.get("/livraison")
def read_livraison():
    return get_livraison()
