## Overview

Posting supports several authentication methods that you can configure in the `Auth` tab of the request editor. When you send a request, Posting generates the appropriate authorization headers automatically.

## Auth types

Select an auth type from the dropdown in the `Auth` tab. The available types are:

- **No Auth** - No authentication headers are sent.
- **Basic** - HTTP Basic authentication using a username and password.
- **Digest** - HTTP Digest authentication using a username and password.
- **Bearer Token** - Sends an `Authorization: Bearer <token>` header with a static token.
- **OAuth2 Client Credentials** - Fetches an access token from an OAuth2 token endpoint using client credentials, then attaches it as a Bearer token.

## Basic auth

Enter a username and password. Posting encodes these as a Base64 `Authorization` header per the HTTP Basic auth spec.

```yaml
auth:
  type: basic
  basic:
    username: my-user
    password: my-password
```

## Digest auth

Enter a username and password. Posting handles the challenge-response flow automatically when the server responds with a `401`.

```yaml
auth:
  type: digest
  digest:
    username: my-user
    password: my-password
```

## Bearer token

Enter a static token. Posting sends it as an `Authorization: Bearer <token>` header.

```yaml
auth:
  type: bearer_token
  bearer_token:
    token: eyJhbGciOi...
```

## OAuth2 Client Credentials

The client credentials grant is designed for service-to-service authentication where no user interaction is required. Posting fetches an access token from the token endpoint before sending your request, and caches it in memory until it expires.

### Fields

- **Token URL** - The OAuth2 token endpoint (e.g. `https://auth.example.com/oauth/token`).
- **Client ID** - Your application's client ID.
- **Client Secret** - Your application's client secret.
- **Scope** - Space-delimited scopes to request (optional).
- **Extra Parameters** - Additional key-value pairs to include in the token request body. Use this for provider-specific parameters like `audience` for Auth0.

```yaml
auth:
  type: oauth2_client_credentials
  oauth2_client_credentials:
    token_url: https://auth.example.com/oauth/token
    client_id: my-client-id
    client_secret: my-client-secret
    scope: read write
    extra_params:
      audience: https://api.example.com
```

### How it works

1. When you send a request, Posting POSTs to the token URL with `grant_type=client_credentials`, your client ID, client secret, scope, and any extra parameters.
2. The token endpoint returns an `access_token` and `expires_in` value.
3. Posting caches the token in memory and attaches it as an `Authorization: Bearer <token>` header.
4. On subsequent requests, the cached token is reused until it expires. Once expired, a fresh token is fetched automatically.

## Using variables

All auth fields support [variable substitution](environments.md). Use `$VARIABLE` or `${VARIABLE}` syntax to reference values from your environment files. This is useful for keeping secrets out of your request files.

```yaml
auth:
  type: oauth2_client_credentials
  oauth2_client_credentials:
    token_url: $TOKEN_URL
    client_id: $CLIENT_ID
    client_secret: $CLIENT_SECRET
```

## Setting auth via scripts

You can also set auth programmatically using [pre-request scripts](scripting.md). See the scripting guide for examples of setting auth on the request object.
