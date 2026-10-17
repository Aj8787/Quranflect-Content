"""Validate the configured FCM credential without delivering any message."""
import argparse
import json
import os
import sys

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from requests.exceptions import RequestException


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-project", required=True)
    args = parser.parse_args()
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "")
    if not raw:
        raise SystemExit("Missing FIREBASE_SERVICE_ACCOUNT repository secret.")
    try:
        info = json.loads(raw)
        if info.get("type") != "service_account":
            raise ValueError("wrong credential type")
        if info.get("project_id") != args.expected_project:
            raise SystemExit("Service-account project does not match the Android Firebase project.")
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )
    except (ValueError, KeyError, GoogleAuthError):
        raise SystemExit("Invalid service-account JSON. Paste the complete downloaded JSON into the secret.") from None
    payload = {
        "validate_only": True,
        "message": {
            "topic": "cards_often",
            "data": {"event_id": "setup-validation", "frequency": "often", "card_id": "setup-validation"},
            "android": {"priority": "high", "ttl": "86400s", "collapse_key": "quranflect_often"},
        },
    }
    try:
        with AuthorizedSession(credentials) as session:
            response = session.post(
                f"https://fcm.googleapis.com/v1/projects/{args.expected_project}/messages:send",
                json=payload, timeout=30,
            )
    except (GoogleAuthError, RequestException):
        raise SystemExit("Could not authenticate or connect to Firebase. Check the service-account key and retry.") from None
    if not response.ok:
        status = "UNKNOWN"
        try:
            status = response.json().get("error", {}).get("status", status)
        except ValueError:
            pass
        raise SystemExit(f"Firebase validation failed: HTTP {response.status_code}, {status}. Check FCM HTTP v1 enablement and Firebase Cloud Messaging API Admin permission.")
    print("PASS: Firebase credentials, project and FCM sending permission validated. No notification was delivered.")


if __name__ == "__main__":
    main()
