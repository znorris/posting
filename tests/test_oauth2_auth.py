"""Tests for OAuth2 Client Credentials httpx.Auth class."""

import json
import time

import httpx
import pytest

from posting.auth import OAuth2ClientCredentialsAuth, OAuth2TokenError
from posting.collection import Auth


def _make_token_response(
    access_token: str = "test-token",
    expires_in: int = 3600,
    status_code: int = 200,
) -> httpx.Response:
    """Build a mock token endpoint response."""
    body = json.dumps({"access_token": access_token, "expires_in": expires_in})
    return httpx.Response(
        status_code=status_code,
        content=body.encode(),
        headers={"content-type": "application/json"},
    )


def _drive_auth_flow(auth: OAuth2ClientCredentialsAuth, url: str = "https://api.example.com/resource"):
    """Drive the auth_flow generator, returning (token_requests, final_request).

    token_requests is a list of httpx.Request objects yielded before the final request.
    final_request is the actual API request with auth headers applied.
    """
    request = httpx.Request("GET", url)
    flow = auth.auth_flow(request)

    token_requests = []
    # Drive the generator
    yielded = next(flow)
    while True:
        # If this yielded request is to the token URL, it's a token fetch
        if yielded.url == httpx.URL(auth.token_url):
            token_requests.append(yielded)
            response = _make_token_response()
            try:
                yielded = flow.send(response)
            except StopIteration:
                pytest.fail("auth_flow stopped before yielding the final request")
        else:
            # This is the final request with auth applied
            try:
                flow.send(_make_token_response())
            except StopIteration:
                pass
            return token_requests, yielded


class TestOAuth2ClientCredentialsAuth:
    def test_auth_flow_fetches_token(self):
        auth = OAuth2ClientCredentialsAuth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
        )
        token_requests, final_request = _drive_auth_flow(auth)

        assert len(token_requests) == 1
        assert final_request.headers["Authorization"] == "Bearer test-token"

    def test_auth_flow_caches_token(self):
        auth = OAuth2ClientCredentialsAuth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
        )
        # First call fetches token
        token_requests_1, _ = _drive_auth_flow(auth)
        # Second call should reuse cached token
        token_requests_2, final_request = _drive_auth_flow(auth)

        assert len(token_requests_1) == 1
        assert len(token_requests_2) == 0
        assert final_request.headers["Authorization"] == "Bearer test-token"

    def test_auth_flow_refreshes_expired_token(self):
        auth = OAuth2ClientCredentialsAuth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
        )
        # First call fetches token
        _drive_auth_flow(auth)
        # Simulate expiry
        auth._expires_at = time.time() - 1
        # Second call should fetch a new token
        token_requests, final_request = _drive_auth_flow(auth)

        assert len(token_requests) == 1
        assert final_request.headers["Authorization"] == "Bearer test-token"

    def test_auth_flow_sends_scope(self):
        auth = OAuth2ClientCredentialsAuth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
            scope="read write",
        )
        token_requests, _ = _drive_auth_flow(auth)

        body = token_requests[0].content.decode()
        assert "scope=read+write" in body or "scope=read%20write" in body

    def test_auth_flow_sends_extra_params(self):
        auth = OAuth2ClientCredentialsAuth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
            extra_params={"audience": "https://api.example.com"},
        )
        token_requests, _ = _drive_auth_flow(auth)

        body = token_requests[0].content.decode()
        assert "audience=https" in body

    @pytest.mark.parametrize("status_code", [401, 403, 500])
    def test_auth_flow_error_on_bad_response(self, status_code: int):
        auth = OAuth2ClientCredentialsAuth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
        )
        request = httpx.Request("GET", "https://api.example.com/resource")
        flow = auth.auth_flow(request)
        next(flow)

        bad_response = _make_token_response(status_code=status_code)
        with pytest.raises(OAuth2TokenError, match=f"status {status_code}"):
            flow.send(bad_response)

    def test_to_httpx_auth_returns_instance(self):
        auth = Auth.oauth2_client_credentials_auth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
            scope="read",
            extra_params={"audience": "https://api.example.com"},
        )
        httpx_auth = auth.to_httpx_auth()
        assert isinstance(httpx_auth, OAuth2ClientCredentialsAuth)
        assert httpx_auth.token_url == "https://auth.example.com/token"
        assert httpx_auth.client_id == "my-client"
        assert httpx_auth.client_secret == "my-secret"
        assert httpx_auth.scope == "read"
        assert httpx_auth.extra_params == {"audience": "https://api.example.com"}
