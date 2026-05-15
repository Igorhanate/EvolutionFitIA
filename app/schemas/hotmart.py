from pydantic import BaseModel


class HotmartBuyer(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    checkout_phone: str | None = None


class HotmartPurchase(BaseModel):
    transaction: str | None = None
    offer: dict | None = None
    status: str | None = None


class HotmartProduct(BaseModel):
    id: int | None = None
    name: str | None = None


class HotmartWebhookPayload(BaseModel):
    event: str
    data: dict | None = None

    def get_buyer(self) -> HotmartBuyer:
        buyer_data = (self.data or {}).get("buyer", {})
        return HotmartBuyer(**buyer_data)

    def get_purchase(self) -> HotmartPurchase:
        purchase_data = (self.data or {}).get("purchase", {})
        return HotmartPurchase(**purchase_data)

    def get_offer_code(self) -> str | None:
        purchase_data = (self.data or {}).get("purchase", {})
        offer = purchase_data.get("offer", {})
        return offer.get("code")

    def get_buyer_phone(self) -> str | None:
        buyer = self.get_buyer()
        phone = buyer.checkout_phone or buyer.phone or ""
        digits = "".join(filter(str.isdigit, phone))
        return digits if digits else None
