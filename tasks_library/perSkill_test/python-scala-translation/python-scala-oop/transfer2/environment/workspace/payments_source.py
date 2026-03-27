from abc import ABC, abstractmethod


class PaymentMethod(ABC):
    def __init__(self, amount: float):
        self.amount = amount

    @abstractmethod
    def charge(self) -> str:
        pass


class Refundable:
    def refund(self) -> str:
        return "refund-issued"


class Auditable:
    def audit_tag(self) -> str:
        return "audit-ok"


class CardPayment(PaymentMethod, Refundable, Auditable):
    def charge(self) -> str:
        return f"card:{self.amount:.2f}"


class WirePayment(PaymentMethod, Auditable):
    def charge(self) -> str:
        return f"wire:{self.amount:.2f}"


class PaymentFactory:
    @staticmethod
    def create(kind: str, amount: float) -> PaymentMethod:
        if kind == "card":
            return CardPayment(amount)
        return WirePayment(amount)
