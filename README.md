<p align="center">
  <img src="https://www.home-assistant.io/images/favicon-192x192.png" height=50>
</p>

<h1 align="center">HA Fleet Monitor</h1>

<p align="center">
  <a href="https://github.com/geertmeersman"><img src="https://img.shields.io/badge/maintainer-Geert%20Meersman-green?style=for-the-badge&logo=github"></a>
  <a href="https://www.buymeacoffee.com/geertmeersman"><img src="https://img.shields.io/badge/Buy%20me%20an%20Omer-donate-yellow?style=for-the-badge&logo=buymeacoffee"></a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg"></a>
  <img src="https://img.shields.io/docker/pulls/geertmeersman/ha-fleet-monitor">
  <img src="https://img.shields.io/docker/v/geertmeersman/ha-fleet-monitor?label=docker%20image%20version">
</p>

<p align="center">
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/actions/workflows/ci.yml"><img src="https://github.com/geertmeersman/ha-fleet-monitor/actions/workflows/ci.yml/badge.svg" alt="CI 🔬"></a>
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/actions/workflows/release.yml"><img src="https://github.com/geertmeersman/ha-fleet-monitor/actions/workflows/release.yml/badge.svg" alt="Release 🚀"></a>
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/actions/workflows/unreleased.yml"><img src="https://github.com/geertmeersman/ha-fleet-monitor/actions/workflows/unreleased.yml/badge.svg" alt="Unreleased changes 🔍"></a>
</p>

<p align="center">
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/issues"><img src="https://img.shields.io/github/issues/geertmeersman/ha-fleet-monitor"></a>
  <a href="http://isitmaintained.com/project/geertmeersman/ha-fleet-monitor"><img src="http://isitmaintained.com/badge/resolution/geertmeersman/ha-fleet-monitor.svg"></a>
  <a href="http://isitmaintained.com/project/geertmeersman/ha-fleet-monitor"><img src="http://isitmaintained.com/badge/open/geertmeersman/ha-fleet-monitor.svg"></a>
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/pulls"><img src="https://img.shields.io/badge/PRs-Welcome-brightgreen.svg"></a>
</p>

<p align="center">
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/releases"><img src="https://img.shields.io/github/v/release/geertmeersman/ha-fleet-monitor?logo=github"></a>
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/releases"><img src="https://img.shields.io/github/release-date/geertmeersman/ha-fleet-monitor"></a>
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/commits"><img src="https://img.shields.io/github/last-commit/geertmeersman/ha-fleet-monitor"></a>
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/graphs/contributors"><img src="https://img.shields.io/github/contributors/geertmeersman/ha-fleet-monitor"></a>
  <a href="https://github.com/geertmeersman/ha-fleet-monitor/commits/main"><img src="https://img.shields.io/github/commit-activity/y/geertmeersman/ha-fleet-monitor?logo=github"></a>
</p>

A self-hosted dashboard to monitor and manage multiple Home Assistant instances from a single interface.

## Features

- 📊 **Dashboard** — Overview of all HA instances with status, version and available updates
- 🔧 **Managed / Monitored** — Split instances into managed (full control) and monitored (read-only)
- 📦 **Update management** — Install individual updates or all updates at once, sequentially per instance
- 🔄 **Restart** — Restart any managed HA instance directly from the dashboard
- ⚠️ **Reboot required** — Visual indicator when a restart is required
- 🛠️ **Admin panel** — Add, edit and remove instances via a web UI (stored in SQLite)
- 📧 **Weekly email report** — Automatic email every Monday at 08:00 with pending updates per instance
- 🧪 **Test mode** — Redirect all emails to a test recipient without affecting production
- 🔐 **Authentication** — Admin account setup on first run, password stored as hash in the database
- 🔑 **Two-factor authentication** — TOTP-based 2FA via any authenticator app
- 🔁 **Password reset** — Reset password via email link
- 💾 **Export / Import** — Export and import instance configuration as JSON
- 🔔 **Attention favicon** — Favicon blinks when updates or a reboot is required
- 🌗 **Light / Dark theme** — Theme toggle with system preference detection
- 🌐 **Multilingual** — EN / NL / FR / DE / ES

## Stack

- **Backend**: Python / Flask
- **Frontend**: Tailwind CSS v3
- **Database**: SQLite
- **Scheduler**: APScheduler
- **Container**: Docker

## Getting Started

### Using Docker Hub (recommended)

No need to clone the repository. Create a `docker-compose.yml`:

```yaml
services:
  ha-fleet-monitor:
    image: geertmeersman/ha-fleet-monitor:latest
    container_name: ha-fleet-monitor
    restart: unless-stopped
    volumes:
      - ./data:/data
    networks:
      - proxy

networks:
  proxy:
    external: true
```

Start:

```bash
docker compose up -d
```

The dashboard is available at the configured proxy URL, or add `ports: - "5000:5000"` to the compose file for direct access.

On first run you will be redirected to `/setup` to create your admin account.

### Building from source

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd ha-fleet-monitor
```

### 2. Build and start

```bash
docker compose up -d --build
```

The dashboard is available at the configured proxy URL, or at `http://localhost:5000` when using the standalone setup.

### 4. Add your HA instances

On first run, go to `http://localhost:5000` — you will be redirected to the setup page to create your admin account (email + password). After that, go to `http://localhost:5000/admin` to add your Home Assistant instances. You'll need a long-lived access token from each HA instance: **Profile → Security → Long-Lived Access Tokens**.

## Supported HA Setups

| Setup | Version detection | Update detection |
|-------|------------------|-----------------:|
| HAOS / Supervised | ✅ via `update.home_assistant_core_update` | ✅ via `update.*` entities |
| Docker (custom sensors) | ✅ via `sensor.current_version` | ✅ via `sensor.docker_hub` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, Tailwind CSS, linting, commit conventions and CI.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
