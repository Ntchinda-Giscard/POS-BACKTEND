from typing import Any, Dict
from ..registry import payment_registry
from ..base import PaymentService
from ..model import PaymentRequest


@payment_registry.register('cash')
class CashPayment(PaymentService):

    def pay(self, request: PaymentRequest) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if request.amountTendered is not None:
            if request.amountTendered < request.amount:
                raise ValueError(
                    f"Montant reçu ({request.amountTendered}) inférieur au montant dû ({request.amount})"
                )
            result["amountTendered"] = request.amountTendered
            result["change"] = round(request.amountTendered - request.amount, 2)
        return result
