# HA Fleet Monitor

A self-hosted dashboard to monitor and manage multiple Home Assistant instances from a single interface.

![Dashboard](https://www.home-assistant.io/images/favicon-192x192.png)

## Features

- 📊 **Dashboard** — Overview of all HA instances with status, version and available updates
- 📦 **Update management** — Install individual updates or all updates at once per instance
- 🔄 **Restart** — Restart any HA instance directly from the dashboard
- ⚠️ **Reboot required** — Visual indicator when a restart is required
- 🛠️ **Admin panel** — Add, edit and remove instances via a web UI (stored in SQLite)
- 📧 **Weekly email report** — Automatic email every Monday at 08:00 with pending updates per instance
- 🧪 **Test mode** — Redirect all emails to a test recipient without affecting production

## Stack

- **Backend**: Python / Flask
- **Frontend**: Tailwind CSS v3
- **Database**: SQLite
- **Scheduler**: APScheduler
- **Container**: Docker

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd ha-monitor
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your SMTP credentials and password:

```env
# Authentication
APP_PASSWORD=your_password
SECRET_KEY=your_random_secret_key

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASS=your_app_password
SMTP_FROM=HA Fleet Monitor <your@email.com>
SMTP_TEST_MODE=false
SMTP_TEST_RECIPIENT=your@email.com
SMTP_ADMIN_CC=your@email.com
```

> **Gmail users**: use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

### 3. Build and start

```bash
docker compose up -d --build
```

The dashboard is available at `http://localhost:5000`.

### 4. Add your HA instances

Go to `http://localhost:5000/admin` and add your Home Assistant instances:

| Field | Description |
|-------|-------------|
| ID | Unique identifier (e.g. `home`, `office`) |
| Name | Display name |
| URL | Full URL including protocol (e.g. `https://ha.example.com`) |
| Token | Long-lived access token from HA → Profile → Security |
| Email | Email address to send update reports to |

#### Generating a Long-Lived Access Token in HA

1. Go to your HA instance
2. Click your profile (bottom left)
3. Scroll to **Long-Lived Access Tokens**
4. Click **Create Token**

## Authentication

All pages and API endpoints are protected by a password. Set `APP_PASSWORD` in `.env` to enable login.

A `SECRET_KEY` is required for secure session encryption — use a long random string:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Email Reports

- Sent automatically every **Monday at 08:00**
- Only sent when updates are available
- One email per instance
- Admin CC receives a copy of every email
- Can be triggered manually via the **Admin panel**

### Test Mode

Set `SMTP_TEST_MODE=true` in `.env` to redirect all emails to `SMTP_TEST_RECIPIENT`. A warning banner will appear in the admin panel when test mode is active.

## Project Structure

```
ha-monitor/
├── templates/
│   ├── index.html       # Dashboard
│   ├── admin.html       # Admin panel
│   └── login.html       # Login page
├── app.py               # Flask app, routes, email logic
├── db.py                # SQLite database helpers
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── tailwind.css         # Tailwind input
├── tailwind.config.js   # Tailwind v3 config
├── .env                 # Your config (not in git)
└── .env.example         # Config template
```

## Supported HA Setups

| Setup | Version detection | Update detection |
|-------|------------------|-----------------|
| HAOS / Supervised | ✅ via `update.home_assistant_core_update` | ✅ via `update.*` entities |
| Docker (custom sensors) | ✅ via `sensor.current_version` | ✅ via `sensor.docker_hub` |
