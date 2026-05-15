from datetime import date, datetime

from pydantic import BaseModel, computed_field


class AssinaturaRead(BaseModel):
    id: int
    user_id: int
    plano: str
    data_inicio: date
    data_fim: date
    status: str
    hotmart_transaction_id: str | None
    created_at: datetime

    @computed_field
    @property
    def is_active(self) -> bool:
        from datetime import date as today_date
        return self.status == "ativo" and self.data_fim >= today_date.today()

    model_config = {"from_attributes": True}
