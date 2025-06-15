from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)
from lnbits.helpers import urlsafe_short_hash
from lnurl.exceptions import InvalidUrl
from lnurl import encode as lnurl_encode

from .crud import (
    create_device,
    delete_device,
    get_device,
    get_devices,
    update_device,
)
from .models import Device, CreateDevice, Switch

partytap_api_router = APIRouter()


@partytap_api_router.post(
    "/api/v1/partytap", dependencies=[Depends(require_admin_key)]
)
async def api_device_create(
    request: Request, data: CreateDevice
) -> Device:

    device_id = urlsafe_short_hash()[:8]

    # compute lnurl for each pin of switch
    url = request.url_for("partytap.lnurl_params",device_id=device_id)
    for switch in data.switches:
        try:
            switch.lnurl = str(lnurl_encode(url + "?switch_id=" + switch.id))
        except InvalidUrl as exc:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Invalid LNURL. `{url!s}`",
            ) from exc

    return await create_device(device_id, data)


@partytap_api_router.put(
    "/api/v1/partytap/{device_id}",
    dependencies=[Depends(require_admin_key)],
)
async def api_device_update(
    request: Request, data: CreateDevice, device_id: str
):
    device = await get_device(device_id)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="partytap device does not exist"
        )

    for k, v in data.dict().items():
        if v is not None:
            setattr(device, k, v)

    # compute lnurl for each pin of switch
    url = request.url_for(
        "partytap.lnurl_params", device_id=device_id
    )
    for switch in data.switches:
        try:
            switch.lnurl = str(lnurl_encode(url + "?switch_id=" + switch.id))
        except InvalidUrl as exc:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Invalid LNURL. `{url!s}`",
            ) from exc

    device.switches = data.switches

    return await update_device(device)


@partytap_api_router.get("/api/v1/partytap")
async def api_devices_retrieve(
    key_info: WalletTypeInfo = Depends(require_invoice_key),
) -> list[Device]:
    user = await get_user(key_info.wallet.user)
    assert user, "partytap cannot retrieve user"
    return await get_devices(user.wallet_ids)


@partytap_api_router.get(
    "/api/v1/partytap/{device_id}",
    dependencies=[Depends(require_invoice_key)],
)
async def api_device_retrieve(device_id: str):
    device = await get_device(device_id)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="partytap device does not exist"
        )
    return device


@partytap_api_router.delete(
    "/api/v1/partytap/{device_id}",
    dependencies=[Depends(require_admin_key)],
)
async def api_device_delete(device_id: str):
    device = await get_device(device_id)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="partytap device does not exist."
        )
    await delete_device(device_id)
