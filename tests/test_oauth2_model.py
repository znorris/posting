"""Tests for OAuth2 Client Credentials data model."""

from posting.collection import Auth, OAuth2ClientCredentials, RequestModel


class TestOAuth2ClientCredentialsModel:
    def test_defaults(self):
        model = OAuth2ClientCredentials()
        assert model.token_url == ""
        assert model.client_id == ""
        assert model.client_secret == ""
        assert model.scope == ""
        assert model.extra_params == {}

    def test_with_values(self):
        model = OAuth2ClientCredentials(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
            scope="read write",
            extra_params={"audience": "https://api.example.com"},
        )
        assert model.token_url == "https://auth.example.com/token"
        assert model.client_id == "my-client"
        assert model.client_secret == "my-secret"
        assert model.scope == "read write"
        assert model.extra_params == {"audience": "https://api.example.com"}


class TestAuthOAuth2Integration:
    def test_type_literal_accepts_oauth2(self):
        auth = Auth(type="oauth2_client_credentials")
        assert auth.type == "oauth2_client_credentials"

    def test_classmethod(self):
        auth = Auth.oauth2_client_credentials_auth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
            scope="read",
            extra_params={"audience": "https://api.example.com"},
        )
        assert auth.type == "oauth2_client_credentials"
        assert auth.oauth2_client_credentials is not None
        assert auth.oauth2_client_credentials.token_url == "https://auth.example.com/token"
        assert auth.oauth2_client_credentials.client_id == "my-client"
        assert auth.oauth2_client_credentials.client_secret == "my-secret"
        assert auth.oauth2_client_credentials.scope == "read"
        assert auth.oauth2_client_credentials.extra_params == {
            "audience": "https://api.example.com"
        }

    def test_to_httpx_auth_returns_none(self):
        """Placeholder until layer 2 adds the real auth class."""
        auth = Auth.oauth2_client_credentials_auth(
            token_url="https://auth.example.com/token",
            client_id="id",
            client_secret="secret",
        )
        assert auth.to_httpx_auth() is None

    def test_model_dump_excludes_defaults(self):
        auth = Auth.oauth2_client_credentials_auth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
        )
        dumped = auth.model_dump(exclude_defaults=True, exclude_none=True)
        assert dumped == {
            "type": "oauth2_client_credentials",
            "oauth2_client_credentials": {
                "token_url": "https://auth.example.com/token",
                "client_id": "my-client",
                "client_secret": "my-secret",
            },
        }

    def test_roundtrip(self):
        auth = Auth.oauth2_client_credentials_auth(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
            scope="read write",
            extra_params={"audience": "https://api.example.com"},
        )
        dumped = auth.model_dump()
        restored = Auth(**dumped)
        assert restored.type == auth.type
        assert restored.oauth2_client_credentials == auth.oauth2_client_credentials


class TestApplyTemplateOAuth2:
    def _make_request(self, **oauth2_kwargs) -> RequestModel:
        return RequestModel(
            url="https://example.com",
            auth=Auth.oauth2_client_credentials_auth(**oauth2_kwargs),
        )

    def test_substitutes_all_fields(self):
        request = self._make_request(
            token_url="https://$DOMAIN/token",
            client_id="$CLIENT_ID",
            client_secret="$CLIENT_SECRET",
            scope="$SCOPE",
        )
        request.apply_template(
            {
                "DOMAIN": "auth.example.com",
                "CLIENT_ID": "my-client",
                "CLIENT_SECRET": "my-secret",
                "SCOPE": "read write",
            }
        )
        oauth2 = request.auth.oauth2_client_credentials
        assert oauth2.token_url == "https://auth.example.com/token"
        assert oauth2.client_id == "my-client"
        assert oauth2.client_secret == "my-secret"
        assert oauth2.scope == "read write"

    def test_substitutes_extra_params(self):
        request = self._make_request(
            token_url="https://auth.example.com/token",
            client_id="id",
            client_secret="secret",
            extra_params={"audience": "$AUDIENCE", "custom": "$CUSTOM"},
        )
        request.apply_template(
            {"AUDIENCE": "https://api.example.com", "CUSTOM": "value"}
        )
        oauth2 = request.auth.oauth2_client_credentials
        assert oauth2.extra_params == {
            "audience": "https://api.example.com",
            "custom": "value",
        }
