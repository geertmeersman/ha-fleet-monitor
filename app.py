import io
import os
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

import pyotp
import qrcode
import qrcode.image.svg
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_babel import Babel
from flask_babel import gettext as _
from werkzeug.security import check_password_hash, generate_password_hash

from db import delete_instance, delete_setting, get_instances, get_setting, init_db, set_setting, upsert_instance

app = Flask(__name__)

with app.app_context():
    init_db()


def _get_or_create_secret_key():
    key = get_setting("secret_key")
    if not key:
        key = secrets.token_hex(32)
        set_setting("secret_key", key)
    return key


app.secret_key = _get_or_create_secret_key()

SUPPORTED_LANGS = ["en", "nl", "fr", "de", "es"]


def get_locale():
    return session.get("lang", "en")


babel = Babel(app, locale_selector=get_locale)


@app.context_processor
def inject_year():
    from datetime import datetime

    version = "unknown"
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")) as f:
            version = f.read().strip()
    except FileNotFoundError:
        pass
    return {"current_year": datetime.now().year, "app_version": version}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def setup_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_setting("password_hash"):
            return redirect(url_for("setup"))
        return f(*args, **kwargs)

    return decorated


def get_smtp_config():
    return {
        "host": get_setting("smtp_host"),
        "port": int(get_setting("smtp_port") or 587),
        "user": get_setting("smtp_user"),
        "password": get_setting("smtp_password"),
        "from": get_setting("smtp_from"),
        "test_mode": (get_setting("smtp_test_mode") or "false").lower() == "true",
        "test_recipient": get_setting("smtp_test_recipient"),
    }


def send_smtp(to, subject, html):
    cfg = get_smtp_config()
    if not all([cfg["host"], cfg["user"], cfg["password"]]):
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from"] or cfg["user"]
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
        server.starttls()
        server.login(cfg["user"], cfg["password"])
        server.sendmail(cfg["from"] or cfg["user"], [to], msg.as_string())
    return True


def check_instance(instance):
    headers = {
        "Authorization": f"Bearer {instance['token']}",
        "Content-Type": "application/json",
    }

    data = {
        "id": instance["id"],
        "name": instance["name"],
        "url": instance["url"],
        "managed": bool(instance.get("managed", 0)),
        "status": "offline",
        "version": "Onbekend",
        "updates": [],
        "reboot_required": False,
    }

    try:
        res = requests.get(f"{instance['url']}/api/states", headers=headers, timeout=4)
        if res.status_code == 200:
            data["status"] = "online"
            states = res.json()
            states_dict = {s.get("entity_id"): s for s in states}

            # --- 1. VERSIE BEPALEN ---
            if "update.home_assistant_core_update" in states_dict:
                core_update = states_dict["update.home_assistant_core_update"]
                data["version"] = core_update.get("attributes", {}).get("installed_version", "Online")
            elif "sensor.current_version" in states_dict:
                data["version"] = states_dict["sensor.current_version"].get("state", "Online")

            # --- 2. UPDATES DETECTEREN ---
            for s in states:
                entity_id = s.get("entity_id", "")
                if entity_id.startswith("update.") and s.get("state") == "on":
                    title = s.get("attributes", {}).get("friendly_name", entity_id)
                    latest = s.get("attributes", {}).get("latest_version", "")
                    data["updates"].append({"entity_id": entity_id, "title": title, "latest": latest})

            has_core_update_entity = "update.home_assistant_core_update" in states_dict
            if not has_core_update_entity and "sensor.docker_hub" in states_dict:
                docker_latest = states_dict["sensor.docker_hub"].get("state")
                current = data["version"]
                if docker_latest and docker_latest not in ["unknown", "unavailable"] and docker_latest != current:
                    data["updates"].append({"title": "Home Assistant Core (Docker)", "latest": docker_latest})

            # --- 3. REBOOT VEREIST ---
            config_res = requests.get(f"{instance['url']}/api/config", headers=headers, timeout=4)
            if config_res.status_code == 200:
                data["reboot_required"] = config_res.json().get("state") == "NEEDS_RESTART"

        elif res.status_code == 401:
            data["status"] = "auth_error"
    except Exception:
        data["status"] = "offline"

    return data


def send_weekly_email():
    from datetime import datetime

    cfg = get_smtp_config()
    smtp_host = cfg["host"]
    smtp_port = cfg["port"]
    smtp_user = cfg["user"]
    smtp_pass = cfg["password"]
    smtp_from = cfg["from"] or smtp_user
    test_mode = cfg["test_mode"]
    test_recipient = cfg["test_recipient"]
    admin_cc = get_setting("admin_email")

    if not all([smtp_host, smtp_user, smtp_pass]):
        print("SMTP niet geconfigureerd, email overgeslagen.", flush=True)
        return

    instances = get_instances()
    for inst in instances:
        result = check_instance(inst)
        if not result["updates"]:
            continue
        email = inst.get("email")
        if not email and not test_mode:
            continue

        actual_recipient = test_recipient if test_mode and test_recipient else email
        if not actual_recipient:
            continue
        if test_mode:
            print(f"[TEST MODE] Email zou naar {email} gaan, wordt verstuurd naar {actual_recipient}", flush=True)

        update_rows = "".join(
            f"""
            <tr>
                <td style='padding:8px 12px;border-bottom:1px solid #e2e8f0;color:#1e293b;font-size:13px'>{u["title"]}</td>
                <td style='padding:8px 12px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;font-family:monospace'>{u["latest"]}</td>
            </tr>"""
            for u in result["updates"]
        )

        reboot_banner = ""
        if result.get("reboot_required"):
            reboot_banner = "<div style='margin-top:8px;padding:8px 12px;background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;color:#c2410c;font-size:12px'>⚠️ Herstart vereist</div>"

        instance_block = f"""
        <div style='margin-bottom:28px'>
            <table style='width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;border:1px solid #e2e8f0'>
                <thead>
                    <tr style='background:#0ea5e9'>
                        <th colspan='2' style='padding:10px 12px;text-align:left;color:#fff;font-size:14px'>
                            🏠 {inst["name"]}
                            <span style='font-weight:normal;font-size:12px;margin-left:8px;opacity:0.85'>v{result["version"]}</span>
                            <a href='{inst["url"]}' style='float:right;color:#fff;font-size:11px;opacity:0.85'>{inst["url"]}</a>
                        </th>
                    </tr>
                    <tr style='background:#f8fafc'>
                        <th style='padding:6px 12px;text-align:left;color:#64748b;font-size:11px;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0'>Component</th>
                        <th style='padding:6px 12px;text-align:left;color:#64748b;font-size:11px;font-weight:600;text-transform:uppercase;border-bottom:1px solid #e2e8f0'>Nieuwe versie</th>
                    </tr>
                </thead>
                <tbody>{update_rows}</tbody>
            </table>
            {reboot_banner}
        </div>"""

        date_str = datetime.now().strftime("%d %B %Y")
        html = f"""
        <!DOCTYPE html><html lang='nl'><head><meta charset='UTF-8'></head>
        <body style='margin:0;padding:0;background:#f1f5f9;font-family:Arial,sans-serif'>
            <table width='100%' cellpadding='0' cellspacing='0' style='background:#f1f5f9;padding:32px 0'>
                <tr><td align='center'>
                    <table width='600' cellpadding='0' cellspacing='0' style='background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08)'>
                        <tr><td style='background:#0f172a;padding:24px 32px'>
                            <img src='https://www.home-assistant.io/images/favicon-192x192.png' width='32' style='vertical-align:middle;margin-right:10px'>
                            <span style='color:#ffffff;font-size:18px;font-weight:bold;vertical-align:middle'>HA Fleet Monitor</span>
                            <p style='color:#94a3b8;font-size:12px;margin:6px 0 0'>Wekelijks updateoverzicht · {date_str}</p>
                        </td></tr>
                        <tr><td style='padding:28px 32px'>
                            <p style='color:#475569;font-size:14px;margin:0 0 24px'>Er zijn updates beschikbaar voor {inst["name"]}:</p>
                            {instance_block}
                        </td></tr>
                        <tr><td style='background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0'>
                            <p style='color:#94a3b8;font-size:11px;margin:0'>Dit is een automatisch bericht van HA Fleet Monitor.</p>
                        </td></tr>
                    </table>
                </td></tr>
            </table>
        </body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{'[TEST] ' if test_mode else ''}HA Fleet Monitor — {inst['name']} heeft updates beschikbaar"
        msg["From"] = smtp_from
        msg["To"] = actual_recipient
        if admin_cc and admin_cc != actual_recipient:
            msg["Cc"] = admin_cc
        msg.attach(MIMEText(html, "html"))

        recipients = [actual_recipient]
        if admin_cc and admin_cc != actual_recipient:
            recipients.append(admin_cc)

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, recipients, msg.as_string())
            print(f"Email verzonden naar {actual_recipient}", flush=True)
        except Exception as e:
            print(f"Email mislukt naar {actual_recipient}: {e}", flush=True)


# --- ROUTES ---


@app.route("/api/set-lang/<lang>")
def set_lang(lang):
    if lang in SUPPORTED_LANGS:
        session["lang"] = lang
    tab = request.args.get("tab")
    if tab == "settings":
        return redirect(url_for("admin_tab", tab="settings"))
    return redirect(url_for("index"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if get_setting("password_hash"):
        return redirect(url_for("login"))
    if request.method == "POST":
        b = request.get_json() if request.is_json else request.form
        email = (b.get("email") or "").strip()
        password = (b.get("password") or "").strip()
        if not email or not password:
            if request.is_json:
                return jsonify({"error": _("Fill in all required fields.")}), 400
            return render_template("setup.html", error=_("Fill in all required fields."))
        set_setting("password_hash", generate_password_hash(password))
        set_setting("admin_email", email)
        session["authenticated"] = True
        if request.is_json:
            return jsonify({"status": "ok"})
        return redirect(url_for("index"))
    return render_template("setup.html", error=None)


@app.route("/login", methods=["GET", "POST"])
@setup_required
def login():
    if request.method == "POST":
        password_hash = get_setting("password_hash")
        if password_hash and check_password_hash(password_hash, request.form.get("password", "")):
            totp_secret = get_setting("totp_secret")
            if totp_secret:
                session["pending_2fa"] = True
                return render_template("login.html", step="totp", error=None)
            session["authenticated"] = True
            return redirect(url_for("index"))
        return render_template("login.html", step="password", error=_("Invalid password"))
    return render_template("login.html", step="password", error=None)


@app.route("/login/totp", methods=["POST"])
@setup_required
def login_totp():
    if not session.get("pending_2fa"):
        return redirect(url_for("login"))
    code = request.form.get("code", "").strip()
    totp_secret = get_setting("totp_secret")
    if totp_secret and pyotp.TOTP(totp_secret).verify(code):
        session.pop("pending_2fa", None)
        session["authenticated"] = True
        return redirect(url_for("index"))
    return render_template("login.html", step="totp", error=_("Invalid code"))


@app.route("/forgot-password", methods=["GET", "POST"])
@setup_required
def forgot_password():
    if request.method == "POST":
        admin_email = get_setting("admin_email")
        if not admin_email:
            return render_template("forgot_password.html", error=_("No admin email configured."), sent=False)
        token = secrets.token_urlsafe(32)
        set_setting("reset_token", token)
        reset_url = url_for("reset_password", token=token, _external=True)
        html = f"<p>Click the link to reset your password:</p><p><a href='{reset_url}'>{reset_url}</a></p><p>This link expires after use.</p>"
        try:
            send_smtp(admin_email, "HA Fleet Monitor — Password reset", html)
            return render_template("forgot_password.html", error=None, sent=True)
        except Exception:
            return render_template(
                "forgot_password.html", error=_("Failed to send email. Check SMTP settings."), sent=False
            )
    return render_template("forgot_password.html", error=None, sent=False)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    stored = get_setting("reset_token")
    if not stored or stored != token:
        return redirect(url_for("login"))
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        if not password:
            return render_template("reset_password.html", token=token, error=_("Fill in all required fields."))
        set_setting("password_hash", generate_password_hash(password))
        delete_setting("reset_token")
        return redirect(url_for("login"))
    return render_template("reset_password.html", token=token, error=None)


@app.route("/api/account", methods=["POST"])
@login_required
def api_account():
    b = request.get_json()
    if b.get("email"):
        set_setting("admin_email", b["email"].strip())
    if b.get("password"):
        current = b.get("current_password", "")
        stored_hash = get_setting("password_hash")
        if not stored_hash or not check_password_hash(stored_hash, current):
            return jsonify({"error": _("Current password is incorrect.")}), 400
        set_setting("password_hash", generate_password_hash(b["password"].strip()))
    return jsonify({"status": "ok"})


@app.route("/api/account", methods=["GET"])
@login_required
def api_account_get():
    return jsonify({"email": get_setting("admin_email") or ""})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/config")
@login_required
def api_config():
    cfg = get_smtp_config()
    return jsonify(
        {
            "test_mode": cfg["test_mode"],
            "test_recipient": cfg["test_recipient"] or "",
        }
    )


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/admin")
@app.route("/admin/<tab>")
@login_required
def admin(tab="instances"):
    return render_template("admin.html")


@app.route("/api/instances", methods=["GET"])
@login_required
def api_get_instances():
    return jsonify(get_instances())


@app.route("/api/instances", methods=["POST"])
@login_required
def api_upsert_instance():
    b = request.get_json()
    upsert_instance(b["id"], b["name"], b["url"], b["token"], b.get("email", ""), b.get("managed", False))
    return jsonify({"status": "ok"})


@app.route("/api/instances/<instance_id>", methods=["DELETE"])
@login_required
def api_delete_instance(instance_id):
    delete_instance(instance_id)
    return jsonify({"status": "ok"})


@app.route("/api/status")
@login_required
def status_api():
    return jsonify([check_instance(inst) for inst in get_instances()])


@app.route("/api/restart", methods=["POST"])
@login_required
def restart_api():
    body = request.get_json()
    inst = next((i for i in get_instances() if i["id"] == body.get("instance_id")), None)
    if not inst:
        return jsonify({"error": "Instantie niet gevonden"}), 404
    headers = {"Authorization": f"Bearer {inst['token']}", "Content-Type": "application/json"}
    res = requests.post(f"{inst['url']}/api/services/homeassistant/restart", headers=headers, json={}, timeout=10)
    return jsonify({"status": "ok" if res.status_code == 200 else "error", "code": res.status_code})


@app.route("/api/update", methods=["POST"])
@login_required
def update_api():
    body = request.get_json()
    inst = next((i for i in get_instances() if i["id"] == body.get("instance_id")), None)
    if not inst:
        return jsonify({"error": "Instantie niet gevonden"}), 404
    headers = {"Authorization": f"Bearer {inst['token']}", "Content-Type": "application/json"}
    res = requests.post(
        f"{inst['url']}/api/services/update/install",
        headers=headers,
        json={"entity_id": body.get("entity_id")},
        timeout=10,
    )
    return jsonify({"status": "ok" if res.status_code == 200 else "error", "code": res.status_code})


@app.route("/api/2fa/setup", methods=["GET"])
@login_required
def api_2fa_setup():
    secret = pyotp.random_base32()
    session["pending_totp_secret"] = secret
    app_name = "HA Fleet Monitor"
    uri = pyotp.TOTP(secret).provisioning_uri(name=app_name, issuer_name=app_name)
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    return jsonify({"secret": secret, "svg": svg})


@app.route("/api/2fa/confirm", methods=["POST"])
@login_required
def api_2fa_confirm():
    secret = session.get("pending_totp_secret")
    code = request.get_json().get("code", "").strip()
    if not secret or not pyotp.TOTP(secret).verify(code):
        return jsonify({"error": _("Invalid code")}), 400
    set_setting("totp_secret", secret)
    session.pop("pending_totp_secret", None)
    return jsonify({"status": "ok"})


@app.route("/api/2fa/disable", methods=["POST"])
@login_required
def api_2fa_disable():
    delete_setting("totp_secret")
    return jsonify({"status": "ok"})


@app.route("/api/2fa/status", methods=["GET"])
@login_required
def api_2fa_status():
    return jsonify({"enabled": get_setting("totp_secret") is not None})


@app.route("/api/smtp", methods=["GET"])
@login_required
def api_smtp_get():
    cfg = get_smtp_config()
    return jsonify(
        {
            "host": cfg["host"] or "",
            "port": cfg["port"],
            "user": cfg["user"] or "",
            "from": cfg["from"] or "",
            "test_mode": cfg["test_mode"],
            "test_recipient": cfg["test_recipient"] or "",
            "configured": bool(cfg["host"] and cfg["user"] and cfg["password"]),
        }
    )


@app.route("/api/smtp", methods=["POST"])
@login_required
def api_smtp_save():
    b = request.get_json()
    for key in ["host", "port", "user", "from", "test_recipient"]:
        if key in b:
            set_setting(f"smtp_{key}", str(b[key]).strip())
    if b.get("password"):
        set_setting("smtp_password", b["password"].strip())
    set_setting("smtp_test_mode", "true" if b.get("test_mode") else "false")
    return jsonify({"status": "ok"})


@app.route("/api/smtp/test", methods=["POST"])
@login_required
def api_smtp_test():
    admin_email = get_setting("admin_email")
    if not admin_email:
        return jsonify({"error": _("No admin email configured.")}), 400
    try:
        send_smtp(admin_email, "HA Fleet Monitor — SMTP test", "<p>SMTP is working correctly.</p>")
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"SMTP test failed: {e}", flush=True)
        return jsonify({"error": _("SMTP test failed. Check your configuration.")}), 500


@app.route("/api/schedule", methods=["GET"])
@login_required
def api_schedule_get():
    return jsonify(
        {
            "day": get_setting("report_day") or "mon",
            "hour": int(get_setting("report_hour") or 8),
        }
    )


@app.route("/api/schedule", methods=["POST"])
@login_required
def api_schedule_save():
    b = request.get_json()
    set_setting("report_day", b.get("day", "mon"))
    set_setting("report_hour", str(b.get("hour", 8)))
    reschedule = app.config.get("reschedule")
    if reschedule:
        reschedule()
    return jsonify({"status": "ok"})


@app.route("/api/send-report/preview", methods=["GET"])
@login_required
def api_send_report_preview():
    cfg = get_smtp_config()
    admin_email = get_setting("admin_email")
    instances = get_instances()
    recipients = []
    for inst in instances:
        email = inst.get("email")
        if cfg["test_mode"] and cfg["test_recipient"]:
            actual = cfg["test_recipient"]
        else:
            actual = email
        if actual and actual not in recipients:
            recipients.append(actual)
    if admin_email and admin_email not in recipients:
        recipients.append(f"{admin_email} (CC)")
    return jsonify({"recipients": recipients, "test_mode": cfg["test_mode"]})


@app.route("/api/send-report", methods=["POST"])
@login_required
def api_send_report():
    send_weekly_email()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    scheduler = BackgroundScheduler()

    def reschedule():
        day = get_setting("report_day") or "mon"
        hour = int(get_setting("report_hour") or 8)
        scheduler.remove_all_jobs()
        scheduler.add_job(send_weekly_email, "cron", day_of_week=day, hour=hour, minute=0)

    reschedule()
    app.config["reschedule"] = reschedule
    scheduler.start()
    app.run(host="0.0.0.0", port=5000)
