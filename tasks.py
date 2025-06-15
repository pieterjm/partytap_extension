import asyncio
import json

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .crud import (
    get_device,
    get_partytap_payment,
    update_partytap_payment,
)


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_partytap")

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "PartyTap":
        return

    partytap_payment = await get_partytap_payment(payment.extra["id"])

    if not partytap_payment:
        return
    if partytap_payment.payment_hash == "paid":
        return
    if partytap_payment.payment_hash == "used":
        return

    partytap_payment.payment_hash = payment.payment_hash
    partytap_payment = await update_partytap_payment(partytap_payment)

    message = json.dumps({
        'event':'paid',
        'payment_hash':partytap_payment.payment_hash,
        'payload':partytap_payment.payload
    })


    return await websocket_updater(
        partytap_payment.device_id,
        message
    )
