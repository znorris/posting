import time
from typing import Generator

import httpx


class HttpxBearerTokenAuth(httpx.Auth):
    def __init__(self, token: str):
        self.token = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


class OAuth2ClientCredentialsAuth(httpx.Auth):
    requires_response_body = True

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str = "",
        extra_params: dict[str, str] | None = None,
    ):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.extra_params = extra_params or {}
        self._token: str | None = None
        self._expires_at: float = 0

    def _is_expired(self) -> bool:
        return self._token is None or time.time() >= self._expires_at

    def _build_token_request(self) -> httpx.Request:
        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scope:
            data["scope"] = self.scope
        data.update(self.extra_params)
        return httpx.Request("POST", self.token_url, data=data)

    def _handle_token_response(self, response: httpx.Response) -> None:
        if response.status_code < 200 or response.status_code >= 300:
            raise OAuth2TokenError(
                f"Token request failed with status {response.status_code}: {response.text}"
            )
        body = response.json()
        if "access_token" not in body:
            raise OAuth2TokenError(
                f"Token response missing access_token: {body}"
            )
        self._token = body["access_token"]
        expires_in = body.get("expires_in", 3600)
        self._expires_at = time.time() + expires_in - 30

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        if self._is_expired():
            token_response = yield self._build_token_request()
            self._handle_token_response(token_response)
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


class OAuth2TokenError(Exception):
    """Raised when the OAuth2 token exchange fails."""
