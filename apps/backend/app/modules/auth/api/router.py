from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import Settings, get_settings
from app.dependencies.auth import get_auth_service, get_current_user
from app.modules.auth.application.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.modules.auth.infrastructure.models.user import UserModel
from app.modules.auth.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: UserModel) -> UserResponse:
    return UserResponse.model_validate(user)


def _set_refresh_cookie(response: Response, settings: Settings, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=token,
        httponly=settings.refresh_token_cookie_httponly,
        secure=settings.refresh_token_cookie_secure,
        samesite=settings.refresh_token_cookie_samesite,
        expires=expires_at,
        path=settings.refresh_token_cookie_path,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path=settings.refresh_token_cookie_path,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    auth: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        user, access_token, expires_in, refresh_token, refresh_expires = await auth.register(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    _set_refresh_cookie(response, settings, refresh_token, refresh_expires)
    return AuthResponse(
        user=_user_response(user),
        access_token=access_token,
        expires_in=expires_in,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    auth: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        user, access_token, expires_in, refresh_token, refresh_expires = await auth.login(
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    _set_refresh_cookie(response, settings, refresh_token, refresh_expires)
    return AuthResponse(
        user=_user_response(user),
        access_token=access_token,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    refresh_token = request.cookies.get(settings.refresh_token_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing.")

    try:
        _, access_token, expires_in, new_refresh_token, refresh_expires = await auth.refresh(
            refresh_token
        )
    except InvalidRefreshTokenError as exc:
        _clear_refresh_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    _set_refresh_cookie(response, settings, new_refresh_token, refresh_expires)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    auth: AuthService = Depends(get_auth_service),
) -> None:
    refresh_token = request.cookies.get(settings.refresh_token_cookie_name)
    await auth.logout(refresh_token)
    _clear_refresh_cookie(response, settings)


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserModel = Depends(get_current_user)) -> UserResponse:
    return _user_response(current_user)
