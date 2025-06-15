import json
from datetime import datetime, timezone
from typing import Optional

from lnurl import encode as lnurl_encode
from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel, Field


class Switch(BaseModel):
    id: str
    amount: float = 0.0
    duration: int = 0
    label: Optional[str]
    lnurl: Optional[str]

class CreateDevice(BaseModel):
    title: str
    wallet: str
    currency: str
    branding: str
    switches: list[Switch]

class Device(BaseModel):
    id: str
    key: str
    title: str
    wallet: str
    currency: str
    branding: str
    switches: list[Switch]
    timestamp: str

class PartytapPayment(BaseModel):
    id: str
    device_id: str
    payment_hash: str
    switch_id: str
    payload: str
    pin: str
    sats: int
    timestamp: str
