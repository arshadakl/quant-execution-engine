"""AngelBroker — Angel One SmartAPI adapter.
Implements IOrderBroker + IDataBroker protocols (data methods added in Task 5).
Uses asyncio.to_thread for all blocking SDK calls.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import pyotp
from SmartApi import SmartConnect

from infrastructure.config.settings import BrokerConfig

logger = logging.getLogger(__name__)

_TOKEN_LIFETIME_HOURS = 23
_REFRESH_BEFORE_MINUTES = 5


class AngelBroker:
    """Wraps Angel One SmartAPI with async interface and auto token refresh."""

    def __init__(self, config: BrokerConfig) -> None:
        self._config = config
        self._smart = SmartConnect(api_key=config.api_key)
        self._jwt_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._feed_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._refresh_lock = asyncio.Lock()

    @property
    def feed_token(self) -> Optional[str]:
        return self._feed_token

    @property
    def jwt_token(self) -> Optional[str]:
        return self._jwt_token

    def _store_session(self, session: dict) -> None:
        """Store JWT, refresh, and feed tokens from a session response dict."""
        self._jwt_token = session["jwtToken"]
        self._refresh_token = session["refreshToken"]
        self._feed_token = session["feedToken"]
        self._token_expiry = datetime.now() + timedelta(hours=_TOKEN_LIFETIME_HOURS)

    async def login(self) -> bool:
        """Authenticate with Angel One using TOTP. Returns True on success."""
        totp = pyotp.TOTP(self._config.totp_secret).now()
        try:
            data = await asyncio.to_thread(
                self._smart.generateSession,
                self._config.client_id,
                self._config.password,
                totp,
            )
            if not data.get("status"):
                logger.error("Login failed: %s", data.get("message"))
                return False
            self._store_session(data["data"])
            logger.info("Authenticated: client=%s", self._config.client_id)
            return True
        except Exception as exc:
            logger.error("Login exception: %s", exc)
            return False

    async def ensure_authenticated(self) -> bool:
        """Check token validity. Refresh if near expiry. Re-login if refresh fails."""
        if self._token_expiry is None:
            return False
        refresh_threshold = datetime.now() + timedelta(minutes=_REFRESH_BEFORE_MINUTES)
        if refresh_threshold < self._token_expiry:
            return True
        async with self._refresh_lock:
            # Re-check inside lock — another coroutine may have refreshed already
            if datetime.now() + timedelta(minutes=_REFRESH_BEFORE_MINUTES) < self._token_expiry:
                return True
            return await self._refresh_or_relogin()

    async def _refresh_or_relogin(self) -> bool:
        try:
            data = await asyncio.to_thread(
                self._smart.generateToken, self._refresh_token
            )
            if not data.get("status"):
                logger.warning("Token refresh failed — re-logging in")
                return await self.login()
            token_data = data["data"]
            self._jwt_token = token_data["jwtToken"]
            if "feedToken" in token_data:
                self._feed_token = token_data["feedToken"]
            if "refreshToken" in token_data:
                self._refresh_token = token_data["refreshToken"]
            self._token_expiry = datetime.now() + timedelta(hours=_TOKEN_LIFETIME_HOURS)
            logger.info("Token refreshed successfully")
            return True
        except Exception as exc:
            logger.error("Token refresh exception: %s — re-logging in", exc)
            return await self.login()

    async def logout(self) -> bool:
        """Terminate the Angel One session. Returns True on success."""
        try:
            data = await asyncio.to_thread(
                self._smart.terminateSession, self._config.client_id
            )
            self._jwt_token = None
            self._refresh_token = None
            self._feed_token = None
            self._token_expiry = None
            logger.info("Session terminated: client=%s", self._config.client_id)
            return bool(data.get("status"))
        except Exception as exc:
            logger.error("Logout exception: %s", exc)
            return False
