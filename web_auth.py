import json
import logging
import os
import secrets
from urllib.parse import urlparse, parse_qs

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


logger = logging.getLogger(__name__)


SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
]

WEB_CREDENTIALS_FILE = "web_credentials.json"

REDIRECT_URI = os.getenv(
    "REDIRECT_URI",
    "http://localhost:5000/oauth2callback",
)


def _load_client_config() -> dict:
    """Loads Google OAuth client configuration."""

    with open(WEB_CREDENTIALS_FILE) as f:
        return json.load(f)["web"]


def get_authorization_url() -> tuple[str, str, str]:
    """Creates the Google OAuth authorization URL and PKCE verifier."""

    code_verifier = secrets.token_urlsafe(64)

    flow = Flow.from_client_secrets_file(
        WEB_CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False,
    )

    flow.code_verifier = code_verifier

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    logger.info("Generated Google OAuth authorization URL")

    return (
        authorization_url,
        state,
        code_verifier,
    )


def exchange_code_for_credentials(
    authorization_response_url: str,
    code_verifier: str,
) -> Credentials:
    """Exchanges the Google authorization code for credentials."""

    parsed = urlparse(authorization_response_url)

    query_params = parse_qs(parsed.query)

    if "error" in query_params:
        error = query_params["error"][0]
        raise RuntimeError(
            f"Google OAuth authorization failed: {error}"
        )

    if "code" not in query_params:
        raise RuntimeError(
            "No authorization code was returned by Google."
        )

    code = query_params["code"][0]

    logger.info("Received Google authorization code")

    flow = Flow.from_client_secrets_file(
        WEB_CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False,
    )

    flow.code_verifier = code_verifier

    logger.info(
        "Exchanging authorization code for Google credentials"
    )

    flow.fetch_token(
        code=code,
        code_verifier=code_verifier,
    )

    credentials = flow.credentials

    logger.info(
        "Google OAuth token exchange successful"
    )

    return credentials
