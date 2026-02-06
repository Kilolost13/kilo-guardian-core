from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from kilo_v2.auth_service import (
    get_appliances,
    get_me,
    get_purchases,
    link_appliance,
    login_user,
    logout_user,
    register_user,
)
from kilo_v2.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


@router.post("/register")
async def register(request: RegisterRequest, response: Response):
    return await register_user(request, response)


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(request: LoginRequest, req: Request, response: Response):
    return await login_user(request, req, response)


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    return await logout_user(response, user)


@router.get("/me")
async def get_me_route(user: dict = Depends(get_current_user)):
    return get_me(user)


class LinkApplianceRequest(BaseModel):
    hardware_id: str
    device_name: str


@router.post("/link-appliance")
async def link_appliance_route(
    request: LinkApplianceRequest, user: dict = Depends(get_current_user)
):
    return await link_appliance(request, user)


@router.get("/appliances")
async def get_appliances_route(user: dict = Depends(get_current_user)):
    return await get_appliances(user)


@router.get("/purchases")
async def get_purchases_route(user: dict = Depends(get_current_user)):
    return await get_purchases(user)
