from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from src.pricing.service import test_pricing_engine_complete
from .model import PricingInput, PricingOutput

router = APIRouter(
    prefix="/pricing",
    tags=["pricing"]
)


@router.post("/", response_model=List[PricingOutput])
def get_pricing(input: List[PricingInput], db: Session = Depends(get_db)) -> List[PricingOutput]:

    result = test_pricing_engine_complete(input, db)

    return result