from typing import Any, Dict
from ..registry import payment_registry
from ..base import PaymentService
from ..model import PaymentRequest


@payment_registry.register('card')
class CardPayment(PaymentService):

    def pay(self, request: PaymentRequest) -> Dict[str, Any]:
        return {"reference": request.reference}
