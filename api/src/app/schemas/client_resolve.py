from __future__ import annotations

from pydantic import BaseModel, Field


class ClientResolveByPhoneResponse(BaseModel):
    client_email_id: str
    client_name: str
    client_business_phone_number: str | None
    collection_name: str
