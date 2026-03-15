import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import requests
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class EnableBankingClient:
    BASE_URL = 'https://api.enablebanking.com'

    def __init__(self, app_id, private_key_pem):
        self.app_id = app_id
        self.private_key_pem = private_key_pem

    def _create_jwt(self):
        iat = int(datetime.now(tz=timezone.utc).timestamp())
        payload = {
            "iss": "enablebanking.com",
            "aud": "api.enablebanking.com",
            "iat": iat,
            "exp": iat + 3600,
        }
        return pyjwt.encode(
            payload,
            self.private_key_pem,
            algorithm="RS256",
            headers={"kid": self.app_id},
        )

    def _headers(self):
        return {"Authorization": f"Bearer {self._create_jwt()}"}

    def list_aspsps(self, country=None):
        params = {}
        if country:
            params["country"] = country

        resp = requests.get(
            f"{self.BASE_URL}/aspsps",
            params=params,
            headers=self._headers(),
            timeout=30,
        )

        if not resp.ok:
            logger.error('Enable Banking GET /aspsps failed %s: %s', resp.status_code, resp.text)

        resp.raise_for_status()
        return resp.json().get("aspsps", [])

    def create_auth(self, aspsp_name, aspsp_country, redirect_url, maximum_consent_validity=None):
        # Use the ASPSP's maximum_consent_validity (seconds) if provided, else fall back to 90 days
        seconds = maximum_consent_validity if maximum_consent_validity else 90 * 24 * 3600
        valid_until = (
            datetime.now(tz=timezone.utc) + timedelta(seconds=seconds)
        ).strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")

        body = {
            "access": {"valid_until": valid_until},
            "aspsp": {"name": aspsp_name, "country": aspsp_country},
            "state": str(uuid.uuid4()),
            "redirect_url": redirect_url,
            "psu_type": "personal",
        }
        resp = requests.post(
            f"{self.BASE_URL}/auth",
            json=body,
            headers=self._headers(),
            timeout=30,
        )

        if not resp.ok:
            logger.error('Enable Banking POST /auth failed %s: %s', resp.status_code, resp.text)

        resp.raise_for_status()
        return resp.json()

    def create_session(self, code):
        resp = requests.post(
            f"{self.BASE_URL}/sessions",
            json={"code": code},
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_transactions(self, account_uid, date_from=None):
        params = {}
        if date_from:
            params["date_from"] = str(date_from)

        transactions = []
        while True:
            resp = requests.get(
                f"{self.BASE_URL}/accounts/{account_uid}/transactions",
                params=params,
                headers=self._headers(),
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            transactions.extend(data.get("transactions", []))
            continuation_key = data.get("continuation_key")

            if not continuation_key:
                break

            params["continuation_key"] = continuation_key

        return {"booked": transactions, "pending": []}


def get_enablebanking_client(organizer):
    app_id = organizer.settings.get('enablebanking_app_id', default='')
    private_key = organizer.settings.get('enablebanking_private_key', default='')

    if not app_id or not private_key:
        raise ImproperlyConfigured('Enable Banking app_id and private_key must be configured.')

    return EnableBankingClient(app_id, private_key)
