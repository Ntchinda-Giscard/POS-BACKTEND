from typing import Any, Dict
from ..registry import payment_registry
from ..base import PaymentService
from ..model import PaymentRequest

PROVIDERS = {"MOMO", "OM"}


@payment_registry.register('digital')
@payment_registry.register('mobile')
class MobilePayment(PaymentService):

    def pay(self, request: PaymentRequest) -> Dict[str, Any]:
        if not request.phone:
            raise ValueError("Le numéro de téléphone est requis pour un paiement mobile")
        provider = (request.provider or "").upper() or None
        if provider and provider not in PROVIDERS:
            raise ValueError(f"Opérateur inconnu: {request.provider} (attendu: {', '.join(sorted(PROVIDERS))})")
        return {"phone": request.phone, "provider": provider, "reference": request.reference}
