from pydantic import BaseModel


class EvolutionMessageKey(BaseModel):
    remoteJid: str
    fromMe: bool
    id: str
    remoteJidAlt: str | None = None
    addressingMode: str | None = None


class EvolutionMessageData(BaseModel):
    key: EvolutionMessageKey | None = None
    message: dict | None = None
    messageType: str | None = None
    messageTimestamp: int | None = None
    pushName: str | None = None


class EvolutionWebhookPayload(BaseModel):
    event: str
    instance: str | None = None
    data: EvolutionMessageData | None = None

    def get_phone(self) -> str | None:
        if not self.data or not self.data.key:
            return None
        key = self.data.key
        # Quando o contato usa LID, usa o JID alternativo com o número real
        if key.addressingMode == "lid" and key.remoteJidAlt:
            jid = key.remoteJidAlt
        else:
            jid = key.remoteJid
        return "".join(filter(str.isdigit, jid.split("@")[0]))

    def get_text(self) -> str | None:
        if not self.data or not self.data.message:
            return None
        msg = self.data.message
        return (
            msg.get("conversation")
            or msg.get("extendedTextMessage", {}).get("text")
            or msg.get("imageMessage", {}).get("caption")
        )

    def get_message_id(self) -> str | None:
        if self.data and self.data.key:
            return self.data.key.id
        return None

    def is_from_me(self) -> bool:
        return bool(self.data and self.data.key and self.data.key.fromMe)

    def is_image(self) -> bool:
        return bool(
            self.data
            and self.data.message
            and self.data.message.get("imageMessage")
        )

    def get_image_mimetype(self) -> str:
        if not self.data or not self.data.message:
            return "image/jpeg"
        return self.data.message.get("imageMessage", {}).get("mimetype", "image/jpeg")
