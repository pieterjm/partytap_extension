from http import HTTPStatus

from fastapi import APIRouter, Query, Request
from lnbits.core.services import create_invoice
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl.types import LnurlPayMetadata
import json

from .crud import (
    create_partytap_payment,
    delete_partytap_payment,
    get_device,
    get_partytap_payment,
    update_partytap_payment,
)

partytap_lnurl_router = APIRouter(prefix="/api/v1/lnurl")


@partytap_lnurl_router.get(
    "{device_id}",
    status_code=HTTPStatus.OK,
    name="partytap.lnurl_params",
)
async def lnurl_params(
    request: Request,
    device_id: str,
    switch_id: str
): 
    device = await get_device(device_id)
    if not device:
        return {
            "status": "ERROR",
            "reason": f"partytap device {device_id} not found on this server",
        }

    # Check they're not trying to trick the switch!
    switch = None
    for _switch in switch.switches:
        if _switch.id == switch_id:
            switch = _switch
            break
    if not switch:
        return {"status": "ERROR", "reason": "Switch params wrong"}
    
    price_msat = int(
        (
            await fiat_amount_as_satoshis(float(switch.amount), device.currency)
            if device.currency != "sat"
            else float(switch.amount)
        )
        * 1000
    )

    partytap_payment = await create_partytap_payment(
        device_id=device.id,
        switch_id=switch.id,
        payload=switch.duration,
        amount_msat=price_msat,
        payment_hash="not yet set",
        pin=""
    )
    if not partytap_payment:
        return {"status": "ERROR", "reason": "Could not create payment."}

    url = str(
        request.url_for(
            "partytap.lnurl_callback", payment_id=partytap_payment.id
        )
    )
    resp = {
        "tag": "payRequest",
        "callback": url,
        "minSendable": price_msat,
        "maxSendable": price_msat,
        "commentAllowed": 255,
        "metadata": LnurlPayMetadata(json.dumps([["text/plain", device.title + "  " + switch.label]])),
    }
    return resp


@partytap_lnurl_router.get(
    "/cb/{payment_id}",
    status_code=HTTPStatus.OK,
    name="partytap.lnurl_callback",
)
async def lnurl_callback( 
    payment_id: str,
    amount: int = Query(None),
    comment: str = Query(None),
):
    partytap_payment = await get_partytap_payment(payment_id)
    if not partytap_payment:
        return {"status": "ERROR", "reason": "partytap payment not found."}
    device = await get_device(partytap_payment.device_id)

    switch = None
    for _switch in device.switches:
        if _switch.id == partytap_payment.switch_id:
            switch = _switch
            break
    
    if not switch:
        await delete_partytap_payment(payment_id)
        return {"status": "ERROR", "reason": "device switch not found."}

    payment = await create_invoice(
        wallet_id=device.wallet,
        amount=int(partytap_payment.sats / 1000),
        memo=f"{device.title} {switch.title}",
        unhashed_description=switch.lnurlpay_metadata.encode(),
        extra={
            "tag": "PartyTap",
            "Device": device.id,
            "Switch": switch.id,
            "amount": switch.amount,
            "currency": device.currency,
            "id": payment_id,
            "received": False,
            "acknowledged": False,
            "fulfilled": False
        },
    )
    partytap_payment.payment_hash = payment.payment_hash
    await update_partytap_payment(partytap_payment)

    message = f"{int(amount / 1000)}sats sent"

    return {
        "pr": payment.bolt11,
        "successAction": {
            "tag": "message",
            "message": message,
        },
        "routes": [],
    }
