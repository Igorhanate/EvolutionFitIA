from pydantic import BaseModel, Field


class MetaProfile(BaseModel):
    name: str | None = None


class MetaContact(BaseModel):
    profile: MetaProfile | None = None
    wa_id: str | None = None


class MetaTextContent(BaseModel):
    body: str | None = None


class MetaMediaContent(BaseModel):
    id: str | None = None
    mime_type: str | None = None
    caption: str | None = None


class MetaMessage(BaseModel):
    model_config = {"populate_by_name": True}

    id: str | None = None
    from_number: str | None = Field(default=None, alias="from")
    timestamp: str | None = None
    type: str | None = None
    text: MetaTextContent | None = None
    image: MetaMediaContent | None = None
    audio: MetaMediaContent | None = None


class MetaValue(BaseModel):
    contacts: list[MetaContact] | None = None
    messages: list[MetaMessage] | None = None


class MetaChange(BaseModel):
    value: MetaValue | None = None
    field: str | None = None


class MetaEntry(BaseModel):
    changes: list[MetaChange] | None = None


class MetaWebhookPayload(BaseModel):
    object: str | None = None
    entry: list[MetaEntry] | None = None

    def _get_message(self) -> MetaMessage | None:
        try:
            return self.entry[0].changes[0].value.messages[0]
        except (IndexError, AttributeError, TypeError):
            return None

    def _get_contacts(self) -> list[MetaContact]:
        try:
            return self.entry[0].changes[0].value.contacts or []
        except (IndexError, AttributeError, TypeError):
            return []

    def get_phone(self) -> str | None:
        msg = self._get_message()
        if not msg or not msg.from_number:
            return None
        return "".join(filter(str.isdigit, msg.from_number))

    def get_text(self) -> str | None:
        msg = self._get_message()
        if not msg:
            return None
        if msg.type == "text" and msg.text:
            return msg.text.body
        if msg.type == "image" and msg.image and msg.image.caption:
            return msg.image.caption
        return None

    def get_message_id(self) -> str | None:
        msg = self._get_message()
        return msg.id if msg else None

    def get_push_name(self) -> str | None:
        msg = self._get_message()
        if not msg or not msg.from_number:
            return None
        for contact in self._get_contacts():
            if contact.wa_id == msg.from_number:
                return contact.profile.name if contact.profile else None
        return None

    def is_message_event(self) -> bool:
        return self._get_message() is not None

    def is_from_me(self) -> bool:
        return False

    def is_image(self) -> bool:
        msg = self._get_message()
        return bool(msg and msg.type == "image")

    def get_image_id(self) -> str | None:
        msg = self._get_message()
        return msg.image.id if msg and msg.image else None

    def get_image_mimetype(self) -> str:
        msg = self._get_message()
        if msg and msg.image and msg.image.mime_type:
            return msg.image.mime_type
        return "image/jpeg"

    def is_audio(self) -> bool:
        msg = self._get_message()
        return bool(msg and msg.type == "audio")

    def get_audio_id(self) -> str | None:
        msg = self._get_message()
        return msg.audio.id if msg and msg.audio else None

    def get_audio_mimetype(self) -> str:
        msg = self._get_message()
        if msg and msg.audio and msg.audio.mime_type:
            return msg.audio.mime_type
        return "audio/ogg; codecs=opus"
