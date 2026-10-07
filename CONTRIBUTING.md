# Contributing

## Dev setup

1. Fork the repository and clone your fork:

```bash
git clone <your-fork>
cd ha-fleet-monitor
```

2. Create a branch for your change:

```bash
git checkout -b feat/my-feature
# or
git checkout -b fix/my-bugfix
```

3. Install dependencies and pre-commit hooks:

```bash
pip install -r requirements.txt
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

4. Create a `.env` file and a `data/` directory:

```bash
cp .env.example .env
mkdir data
```

Set `APP_PASSWORD` to a password of your choice and `SECRET_KEY` to a random value:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

`SECRET_KEY` is used by Flask to sign session cookies. Changing it will log out all active users.

SMTP variables (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`) are optional — if `SMTP_HOST` is not set, the weekly email job is skipped silently.

Set `SMTP_TEST_MODE=true` to redirect all outgoing emails to `SMTP_TEST_RECIPIENT` during development.

5. Start the dev server:

```bash
flask --app app.py run
```

Open [http://localhost:5000](http://localhost:5000) and log in with your `APP_PASSWORD`.

6. Add your HA instances via [http://localhost:5000/admin](http://localhost:5000/admin).

7. Make your changes, then open a pull request against `main`. The PR title must follow [Conventional Commits](#commit-messages).

## Tailwind CSS

Tailwind v3 is compiled from `tailwind.css` using the standalone CLI. The output `static/tailwind.css` is generated at Docker build time and excluded from version control.

To rebuild locally:

```bash
curl -fsSL https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64 \
  -o tailwindcss && chmod +x tailwindcss
./tailwindcss -i tailwind.css -o static/tailwind.css --minify --config tailwind.config.js
```

## Linting & formatting

[Ruff](https://docs.astral.sh/ruff/) is used for both linting and formatting. It runs automatically before every commit via pre-commit. To run manually:

```bash
ruff check .          # lint
ruff format .         # format
ruff check --fix .    # lint + auto-fix
```

## Commit messages

Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

feat:     new feature
fix:      bug fix
docs:     documentation only
style:    formatting, no logic change
refactor: code change that is neither a fix nor a feature
chore:    build process, dependencies
ci:       CI/CD changes
```

Examples:
```
feat: add reboot required banner
fix: correct update detection for docker instances
docs: update contributing guide
```

## CI

GitHub Actions runs the following jobs on every push and pull request to `main`:

| Job | What it does |
|-----|-------------|
| `ruff` | Lint + format check |
| `docker` | Verifies the Docker image builds cleanly |
