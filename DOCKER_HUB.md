<p align="center">
  <img src="https://www.home-assistant.io/images/favicon-192x192.png" height=50>
</p>

<h1 align="center">HA Fleet Monitor</h1>

<p align="center" style="display: flex;">
  <a href="https://github.com/geertmeersman"><img src="https://img.shields.io/badge/maintainer-Geert%20Meersman-green?style=for-the-badge&logo=github"></a>
  <a href="https://www.buymeacoffee.com/geertmeersman"><img src="https://img.shields.io/badge/Buy%20me%20an%20Omer-donate-yellow?style=for-the-badge&logo=buymeacoffee"></a>
</p>

A self-hosted dashboard to monitor and manage multiple Home Assistant instances from a single interface.

## Features

- 📊 **Dashboard** — Overview of all HA instances with status, version and available updates
- 📦 **Update management** — Install individual updates or all updates at once per instance
- 🔄 **Restart** — Restart any HA instance directly from the dashboard
- ⚠️ **Reboot required** — Visual indicator when a restart is required
- 🛠️ **Admin panel** — Add, edit and remove instances via a web UI (stored in SQLite)
- 📧 **Weekly email report** — Automatic email every Monday at 08:00 with pending updates per instance
- 🧪 **Test mode** — Redirect all emails to a test recipient without affecting production
- 🔐 **Authentication** — Password protected via `.env`
- 🔔 **Attention favicon** — Favicon blinks when updates or a reboot is required
- 🌐 **Multilingual** — EN / NL / FR / DE / ES

## Quick start

Create a `docker-compose.yml`:

**With reverse proxy (no exposed port):**

```yaml
services:
  ha-monitor:
    image: geertmeersman/ha-fleet-monitor:latest
    container_name: ha-fleet-monitor
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/data
    networks:
      - proxy

networks:
  proxy:
    external: true
```

**Standalone (with exposed port):**

```yaml
services:
  ha-monitor:
    image: geertmeersman/ha-fleet-monitor:latest
    container_name: ha-fleet-monitor
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/data
    ports:
      - "5000:5000"
```

Create a `.env` file:

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

Then start:

```bash
docker compose up -d
```

The dashboard is available at the configured proxy URL, or at `http://localhost:5000` when using the standalone setup.

## Supported HA Setups

| Setup | Version detection | Update detection |
|-------|------------------|-----------------|
| HAOS / Supervised | ✅ via `update.home_assistant_core_update` | ✅ via `update.*` entities |
| Docker (custom sensors) | ✅ via `sensor.current_version` | ✅ via `sensor.docker_hub` |

## Links

- 📖 [Full documentation & source code](https://github.com/geertmeersman/ha-fleet-monitor)
- 🐛 [Report an issue](https://github.com/geertmeersman/ha-fleet-monitor/issues)
- 📋 [Changelog](https://github.com/geertmeersman/ha-fleet-monitor/releases)
- 📜 [License — GPLv3](https://github.com/geertmeersman/ha-fleet-monitor/blob/main/LICENSE)
