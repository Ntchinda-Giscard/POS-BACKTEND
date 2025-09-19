from typing import List
from fastapi import APIRouter
from src.pricing.service import test_pricing_engine_complete
from .model import PricingInput, PricingOutput

router = APIRouter(
    prefix="/pricing",
    tags=["pricing"]
)


@router.post("/", response_model=PricingOutput)
def get_pricing(input: List[PricingInput]) -> PricingOutput:

    result = test_pricing_engine_complete(input)

    return result