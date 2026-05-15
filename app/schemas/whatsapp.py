from pydantic import BaseModel


class EvolutionMessageKey(BaseModel):
    remoteJid: str
    fromMe: bool
    id: str


class EvolutionMessageData(BaseModel):
    key: EvolutionMessageKey
    message: dict | None = None
    messageType: str | None = None
    messageTimestamp: int | None = None
    pushName: str | None = None


class EvolutionWebhookPayload(BaseModel):
    event: str
    instance: str | None = None
    data: EvolutionMessageData | None = None

    def get_phone(self) -> str | None:
        if self.data and self.data.key:
            jid = self.data.key.remoteJid
            return "".join(filter(str.isdigit, jid.split("@")[0]))
        return None

    def get_text(self) -> str | None:
        if not self.data or not self.data.message:
            return None
        msg = self.data.message
        return (
            msg.get("conversation")
            or msg.get("extendedTextMessage", {}).get("text")
            or msg.get("imageMessage", {}).get("caption")
        )

    def is_from_me(self) -> bool:
        return bool(self.data and self.data.key and self.data.key.fromMe)
