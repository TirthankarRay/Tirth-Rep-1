"""
Shared authentication helper for Lambda functions.

Validates JWT tokens issued by Amazon Cognito by verifying the signature
against the user pool's JSON Web Key Set (JWKS).  Returns the decoded
claims on success or raises ``UnauthorizedError`` on failure.
"""

import json
import logging
import os
import urllib.request

from jose import jwt, JWTError, jwk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Derived values
_ISSUER = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
_JWKS_URL = f"{_ISSUER}/.well-known/jwks.json"

# Cache the JWKS across invocations within the same Lambda container
_jwks_cache: dict | None = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class UnauthorizedError(Exception):
    """Raised when a request cannot be authenticated."""

    def __init__(self, message: str = "Unauthorized"):
        self.message = message
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _get_jwks() -> dict:
    """Download and cache the Cognito user pool JWKS."""

    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    logger.info("Fetching JWKS from %s", _JWKS_URL)
    try:
        with urllib.request.urlopen(_JWKS_URL, timeout=5) as resp:
            _jwks_cache = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.error("Failed to fetch JWKS: %s", exc)
        raise UnauthorizedError("Unable to fetch authentication keys") from exc

    return _jwks_cache


def _extract_token(event: dict) -> str:
    """Extract the Bearer token from the Authorization header.

    Supports both API Gateway v1 (``headers``) and v2 (``headers`` with
    lower-case keys) payload formats.
    """

    headers = event.get("headers") or {}

    # API Gateway may deliver headers with original or lower-cased keys
    auth_header = headers.get("Authorization") or headers.get("authorization")

    if not auth_header:
        raise UnauthorizedError("Missing Authorization header")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Authorization header must use Bearer scheme")

    return parts[1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def validate_token(event: dict) -> dict:
    """Validate the JWT from the request's Authorization header.

    Parameters
    ----------
    event : dict
        The API Gateway Lambda proxy event.

    Returns
    -------
    dict
        Decoded JWT claims including ``sub``, ``email``, and
        ``cognito:groups`` (if present).

    Raises
    ------
    UnauthorizedError
        If the token is missing, malformed, expired, or has an invalid
        signature.
    """

    token = _extract_token(event)

    # Decode the header to find the key ID (kid)
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise UnauthorizedError(f"Invalid token header: {exc}") from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise UnauthorizedError("Token header missing 'kid'")

    # Look up the matching public key from JWKS
    jwks_data = _get_jwks()
    rsa_key: dict | None = None
    for key in jwks_data.get("keys", []):
        if key.get("kid") == kid:
            rsa_key = key
            break

    if rsa_key is None:
        # Refresh JWKS in case of key rotation, then retry once
        global _jwks_cache
        _jwks_cache = None
        jwks_data = _get_jwks()
        for key in jwks_data.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

    if rsa_key is None:
        raise UnauthorizedError("Unable to find matching signing key")

    # Verify and decode the token
    try:
        claims = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=None,  # Cognito access tokens do not include an aud claim
            issuer=_ISSUER,
            options={
                "verify_aud": False,
                "verify_exp": True,
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except JWTError as exc:
        raise UnauthorizedError(f"Token validation failed: {exc}") from exc

    logger.info(
        "Authenticated user: sub=%s email=%s groups=%s",
        claims.get("sub"),
        claims.get("email"),
        claims.get("cognito:groups"),
    )

    return claims
