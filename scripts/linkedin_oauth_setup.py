"""One-time LinkedIn OAuth2 setup — generates auth URL, accepts callback code, stores access token."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

import httpx

TOKEN_PATH = Path(os.getenv("MEMORY_DIR", "./memory")) / "linkedin_token.json"
REDIRECT_URI = "http://localhost:3000/oauth/callback"

# LinkedIn OAuth2 scopes
# openid + profile + email = Sign In with LinkedIn
# w_member_social = post/comment on behalf of member
SCOPES = "openid profile email w_member_social"


def generate_auth_url():
    """Step 1: Generate LinkedIn authorization URL."""
    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    if not client_id:
        print("ERROR: Set LINKEDIN_CLIENT_ID in .env")
        sys.exit(1)

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&state=linkedin_fte_auth"
    )

    print("\n=== Step 1: Open this URL in your browser ===\n")
    print(f"{auth_url}\n")
    print("After authorizing, you will be redirected to a URL like:")
    print("  http://localhost:3000/oauth/callback?code=XXXX&state=linkedin_fte_auth")
    print("\nCopy the FULL redirect URL from your browser address bar.")
    print("Then run:  python scripts/linkedin_oauth_setup.py --callback 'PASTE_URL_HERE'")
    print("\nOr just pass the code directly:")
    print("  python scripts/linkedin_oauth_setup.py --code 'THE_CODE_VALUE'")


def exchange_code(code: str):
    """Step 2: Exchange authorization code for access token."""
    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("ERROR: Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env")
        sys.exit(1)

    response = httpx.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status_code != 200:
        print(f"ERROR: Token exchange failed ({response.status_code})")
        print(response.text)
        sys.exit(1)

    token_data = response.json()
    access_token = token_data.get("access_token", "")
    expires_in = token_data.get("expires_in", 0)

    # Save token
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token_data, indent=2), encoding="utf-8")

    print(f"\nAccess token saved to {TOKEN_PATH.resolve()}")
    print(f"Token expires in {expires_in // 86400} days ({expires_in}s)")

    # Fetch profile to verify
    profile = _verify_token(access_token)
    if profile:
        name = profile.get("name", profile.get("localizedFirstName", "Unknown"))
        print(f"Authenticated as: {name}")

    print(f"\nUpdate your .env file:")
    print(f"  LINKEDIN_ACCESS_TOKEN={access_token}")
    print(f"\nLinkedIn OAuth2 setup complete.")


def _verify_token(access_token: str) -> dict | None:
    """Verify token by fetching user profile."""
    try:
        response = httpx.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--callback":
        callback_url = sys.argv[2]
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if not code:
            print("ERROR: Could not extract 'code' from the callback URL.")
            sys.exit(1)
        exchange_code(code)

    elif len(sys.argv) >= 3 and sys.argv[1] == "--code":
        exchange_code(sys.argv[2])

    else:
        generate_auth_url()


if __name__ == "__main__":
    main()
