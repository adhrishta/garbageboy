import os, json, time, smtplib
from datetime import datetime
from pathlib import Path
from email.message import EmailMessage
from email.utils import formataddr

CONFIG_FILE = "config.json"
LOG_FILE = "deleted_files.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

def load_and_validate_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("Missing config.json")

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    if "target_path" not in config or not isinstance(config["target_path"], str):
        raise ValueError("Missing or invalid 'target_path'")
    if "days_threshold" not in config or not isinstance(config["days_threshold"], int):
        raise ValueError("Missing or invalid 'days_threshold'")

    target_path = config["target_path"].replace("/", os.sep)
    if not os.path.isdir(target_path):
        raise FileNotFoundError(f"Directory not found: {target_path}")

    return config, target_path, config["days_threshold"]

def delete_old_files(folder, days):
    now = time.time()
    cutoff = now - days * 86400

    for root, _, files in os.walk(folder):
        for f in files:
            file_path = os.path.join(root, f)
            try:
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    if mtime < cutoff:
                        os.remove(file_path)
                        log(f"Deleted: {file_path}")
            except Exception as e:
                log(f"Error deleting {file_path}: {e}")

def send_email(config):
    mail_cfg = config.get("email_config", {})
    if not mail_cfg.get("enabled", False):
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = "File Cleanup Log Report"
        msg["From"] = formataddr(("File Cleanup", mail_cfg["sender_email"]))
        msg["To"] = mail_cfg["recipient_email"]
        msg.set_content("Attached is the latest file cleanup log.")

        with open(LOG_FILE, "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="plain", filename="deleted_files.log")

        server = smtplib.SMTP(mail_cfg["smtp_host"], mail_cfg["smtp_port"])
        if mail_cfg.get("use_tls", False):
            server.starttls()

        server.login(mail_cfg["sender_email"], mail_cfg["sender_password"])
        server.send_message(msg)
        server.quit()
        log("Email sent successfully.")
    except Exception as e:
        log(f"Failed to send email: {e}")

def main():
    try:
        config, folder, days = load_and_validate_config()
        log("=== Cleanup started ===")
        delete_old_files(folder, days)
        send_email(config)
    except Exception as e:
        log(f"FATAL: {e}")
        try:
            send_email(config)
        except:
            pass
        raise SystemExit(1)

if __name__ == "__main__":
    main()
