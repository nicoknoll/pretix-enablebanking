# pretix-enablebanking

Connects pretix to your bank via [Enable Banking](https://enablebanking.com) (PSD2/Open Banking). Once configured, it periodically fetches bank transactions and feeds them into pretix's bank transfer pipeline — automatically matching incoming payments to orders.

**Key capabilities:**
- OAuth-based bank connection via 400+ European banks (PSD2)
- Automatic and on-demand transaction import
- Multi-account support with per-account activation toggle
- Configurable auto-fetch interval (every 1h, 4h, 12h, or 24h)
- Works at organizer level (one connection per organizer)

## Screenshots

**Import — manual fetch & job history**

![Import](docs/images/import.png)

**Settings — bank connection & API credentials**

![Settings](docs/images/settings.png)

## How it works

1. You register an app at Enable Banking and get an App ID + RSA private key.
2. You enter those credentials in the plugin settings and initiate an OAuth flow to connect your bank account.
3. After authorization, Enable Banking provides access to your bank accounts. You activate the ones you want to import from.
4. The plugin fetches transactions (automatically or on demand) and creates `BankImportJob` records, which pretix then processes to match payments against open orders.

The transaction import runs as a Celery task and uses Enable Banking's paginated transactions API. The last-fetched date per account is tracked to avoid re-importing.

## Installation

Clone the repo and install into your pretix virtualenv:

```bash
git clone https://github.com/nicoknoll/pretix-enablebanking.git
cd pretix-enablebanking
pip install -e .
```

Then run migrations and restart the server:

```bash
python -m pretix migrate
```

The plugin registers itself automatically via the `pretix.plugin` entry point — no manual `INSTALLED_APPS` edit needed.

## Setup in pretix

### 1. Get Enable Banking credentials

1. Sign up at [developers.enablebanking.com](https://developers.enablebanking.com) and create an application.
2. Generate an RSA key pair. Register the public key with Enable Banking and keep the private key (PEM format).
3. Note your **Application ID**.

### 2. Configure the plugin

In the pretix backend, go to your organizer → **Bank transfer** → **Enable Banking settings**:

- **Application ID** — the App ID from Enable Banking
- **Private key (PEM)** — your RSA private key (`-----BEGIN PRIVATE KEY-----` format)
- **Country** — used to filter the list of available banks (ASPSPs)
- **Auto-fetch interval** — how often transactions should be fetched automatically (set to "disabled" to import manually only)

Save, then select your bank from the dropdown and click **Connect with bank**. You'll be redirected to Enable Banking's hosted authorization page where you log into your bank and grant consent.

After authorization, you're redirected back and your accounts appear in the settings. Activate the accounts you want to import from and save.

### 3. Import transactions

Go to **Bank transfer** → **Automatic import** to:

- Trigger a manual import (optionally specify a start date)
- View recent import jobs and their status
- See when your bank connection expires (Enable Banking consent is typically valid for 90 days — renew before it expires)

## Testing with the sandbox

Enable Banking provides a sandbox environment with a mock bank. Use these credentials when connecting **Aachener Bank** (country: **DE**):

| Field | Value |
|---|---|
| VR NetKey | `VRK1234567890ALL` |
| PIN | `password` |
| OTP | `123456` |

The import view shows a **Sandbox mode** warning when a mock bank is connected.

## Dependencies

| Package | Purpose |
|---|---|
| `pretix >= 2.7.0` | Host platform |
| `requests` | HTTP calls to Enable Banking API |
| `PyJWT` | RS256-signed JWT for API authentication (transitive via pretix) |

Python 3.10+ required.

## Permissions

The plugin operates at organizer level. Users need **can_change_organizer_settings** to access settings and trigger imports.

## License

MIT — see [LICENSE](LICENSE).