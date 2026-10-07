import os
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, jsonify, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler
from db import init_db, get_instances, upsert_instance, delete_instance

app = Flask(__name__)

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
        "reboot_required": False
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

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user)
    test_mode = os.environ.get("SMTP_TEST_MODE", "false").lower() == "true"
    test_recipient = os.environ.get("SMTP_TEST_RECIPIENT")
    admin_cc = os.environ.get("SMTP_ADMIN_CC")

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

        update_rows = "".join(f"""
            <tr>
                <td style='padding:8px 12px;border-bottom:1px solid #e2e8f0;color:#1e293b;font-size:13px'>{u['title']}</td>
                <td style='padding:8px 12px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;font-family:monospace'>{u['latest']}</td>
            </tr>""" for u in result["updates"])

        reboot_banner = ""
        if result.get("reboot_required"):
            reboot_banner = "<div style='margin-top:8px;padding:8px 12px;background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;color:#c2410c;font-size:12px'>⚠️ Herstart vereist</div>"

        instance_block = f"""
        <div style='margin-bottom:28px'>
            <table style='width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;border:1px solid #e2e8f0'>
                <thead>
                    <tr style='background:#0ea5e9'>
                        <th colspan='2' style='padding:10px 12px;text-align:left;color:#fff;font-size:14px'>
                            🏠 {inst['name']}
                            <span style='font-weight:normal;font-size:12px;margin-left:8px;opacity:0.85'>v{result['version']}</span>
                            <a href='{inst['url']}' style='float:right;color:#fff;font-size:11px;opacity:0.85'>{inst['url']}</a>
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
                            <p style='color:#475569;font-size:14px;margin:0 0 24px'>Er zijn updates beschikbaar voor {inst['name']}:</p>
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

@app.route("/api/config")
def api_config():
    return jsonify({
        "test_mode": os.environ.get("SMTP_TEST_MODE", "false").lower() == "true",
        "test_recipient": os.environ.get("SMTP_TEST_RECIPIENT", "")
    })

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/api/instances", methods=["GET"])
def api_get_instances():
    return jsonify(get_instances())

@app.route("/api/instances", methods=["POST"])
def api_upsert_instance():
    b = request.get_json()
    upsert_instance(b["id"], b["name"], b["url"], b["token"], b.get("email", ""), b.get("managed", False))
    return jsonify({"status": "ok"})

@app.route("/api/instances/<instance_id>", methods=["DELETE"])
def api_delete_instance(instance_id):
    delete_instance(instance_id)
    return jsonify({"status": "ok"})

@app.route("/api/status")
def status_api():
    return jsonify([check_instance(inst) for inst in get_instances()])

@app.route("/api/restart", methods=["POST"])
def restart_api():
    body = request.get_json()
    inst = next((i for i in get_instances() if i["id"] == body.get("instance_id")), None)
    if not inst:
        return jsonify({"error": "Instantie niet gevonden"}), 404
    headers = {"Authorization": f"Bearer {inst['token']}", "Content-Type": "application/json"}
    res = requests.post(f"{inst['url']}/api/services/homeassistant/restart", headers=headers, json={}, timeout=10)
    return jsonify({"status": "ok" if res.status_code == 200 else "error", "code": res.status_code})

@app.route("/api/update", methods=["POST"])
def update_api():
    body = request.get_json()
    inst = next((i for i in get_instances() if i["id"] == body.get("instance_id")), None)
    if not inst:
        return jsonify({"error": "Instantie niet gevonden"}), 404
    headers = {"Authorization": f"Bearer {inst['token']}", "Content-Type": "application/json"}
    res = requests.post(f"{inst['url']}/api/services/update/install", headers=headers, json={"entity_id": body.get("entity_id")}, timeout=10)
    return jsonify({"status": "ok" if res.status_code == 200 else "error", "code": res.status_code})

@app.route("/api/send-report", methods=["POST"])
def api_send_report():
    send_weekly_email()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_weekly_email, "cron", day_of_week="mon", hour=8, minute=0)
    scheduler.start()
    app.run(host="0.0.0.0", port=5000)
