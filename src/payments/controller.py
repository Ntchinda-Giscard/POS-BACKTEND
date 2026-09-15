import logging
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from .registry import payment_registry
from .model import PaymentDetail, PaymentRequest, PaymentResponse
from .service import get_payment_detail, list_payments, record_payment

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post('/process', response_model=PaymentResponse)
def process_payment(request: PaymentRequest, db: Session = Depends(get_db)):
    if request.amount <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le montant doit être supérieur à zéro")
    try:
        payment_service_class = payment_registry.get(request.method)
        details = payment_service_class().pay(request)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    try:
        payment = record_payment(request, details, db)
    except LookupError as e:
        # no open cash session on this site
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    logger.info(f"Registered payment {payment.transactionId} for order {payment.orderId} ({payment.method} {payment.amount}) by {payment.userCode}")
    return payment


@router.get('/', response_model=List[PaymentResponse])
def read_payments(
    order_id: Optional[str] = None,
    day: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    method: Optional[str] = None,
    user_code: Optional[str] = None,
    session_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """List registered payments, most recent first."""
    return list_payments(db, order_id=order_id, day=day, date_from=date_from, date_to=date_to,
                         method=method, user_code=user_code, session_id=session_id, search=search, limit=limit)


@router.get('/{transaction_id}', response_model=PaymentDetail)
def read_payment(transaction_id: str, db: Session = Depends(get_db)):
    """One payment with the order lines behind it (for reprinting a receipt)."""
    detail = get_payment_detail(db, transaction_id)
    if not detail:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paiement introuvable")
    return detail
