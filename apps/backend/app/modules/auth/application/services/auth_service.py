from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.auth.application.services import security
from app.modules.auth.infrastructure.models.refresh_token import RefreshTokenModel
from app.modules.auth.infrastructure.models.user import UserModel


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def register(self, email: str, password: str, full_name: str | None = None) -> tuple[UserModel, str, int, str, datetime]:
        normalized_email = email.strip().lower()
        if await self._email_exists(normalized_email):
            raise EmailAlreadyRegisteredError("Email is already registered.")

        user = UserModel(
            email=normalized_email,
            hashed_password=security.hash_password(password),
            full_name=full_name,
        )
        self._session.add(user)
        await self._session.flush()
        return await self._issue_tokens(user)

    async def login(self, email: str, password: str) -> tuple[UserModel, str, int, str, datetime]:
        user = await self._get_user_by_email(email)
        if user is None or not security.verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password.")
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive.")
        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> tuple[UserModel, str, int, str, datetime]:
        token_hash = security.hash_refresh_token(refresh_token)
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        user = await self._session.get(UserModel, stored.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        stored.revoked_at = now
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        token_hash = security.hash_refresh_token(refresh_token)
        await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.token_hash == token_hash,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def get_user_by_id(self, user_id: UUID) -> UserModel | None:
        user = await self._session.get(UserModel, user_id)
        if user is None or not user.is_active:
            return None
        return user

    async def _issue_tokens(
        self, user: UserModel
    ) -> tuple[UserModel, str, int, str, datetime]:
        access_token, expires_in = security.create_access_token(
            user_id=user.id,
            email=user.email,
            secret=self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
            minutes=self._settings.jwt_access_token_expire_minutes,
        )
        refresh_token = security.generate_refresh_token()
        refresh_expires_at = datetime.now(UTC) + timedelta(days=self._settings.refresh_token_expire_days)
        self._session.add(
            RefreshTokenModel(
                user_id=user.id,
                token_hash=security.hash_refresh_token(refresh_token),
                expires_at=refresh_expires_at,
            )
        )
        await self._session.flush()
        return user, access_token, expires_in, refresh_token, refresh_expires_at

    async def _email_exists(self, email: str) -> bool:
        result = await self._session.execute(
            select(UserModel.id).where(func.lower(UserModel.email) == email)
        )
        return result.scalar_one_or_none() is not None

    async def _get_user_by_email(self, email: str) -> UserModel | None:
        normalized = email.strip().lower()
        result = await self._session.execute(
            select(UserModel).where(func.lower(UserModel.email) == normalized)
        )
        return result.scalar_one_or_none()
