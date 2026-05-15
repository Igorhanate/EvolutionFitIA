from datetime import datetime

from pydantic import BaseModel


class UsuarioRead(BaseModel):
    id: int
    telefone: str
    nome: str | None
    email: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
