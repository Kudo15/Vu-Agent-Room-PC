"""Configure the admin IMAP reader without putting a password on the command line."""
from __future__ import annotations

import getpass
import json
from pathlib import Path

from key_store import read_keys, write_keys
from mailbox_reader import DATA, PASSWORD_KEY, SETTINGS


def main():
    print("Cấu hình đọc thư IMAP cho Agent Room và Codex. Không gửi thư.")
    host = input("IMAP host [mail.vuhocai.shop]: ").strip() or "mail.vuhocai.shop"
    username = input("Tài khoản [admin@vuhocai.shop]: ").strip() or "admin@vuhocai.shop"
    password = getpass.getpass("Mật khẩu mailbox (ẩn): ")
    if not password:
        raise SystemExit("Chưa nhập mật khẩu; không lưu cấu hình.")
    if any(c in password for c in "\r\n"):
        raise SystemExit("Mật khẩu không hợp lệ.")
    # Validate before modifying either local settings file.
    import re
    if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host) or not re.fullmatch(r"[^\s@]+@[^\s@]+", username):
        raise SystemExit("Host hoặc tài khoản không hợp lệ.")
    DATA.mkdir(parents=True, exist_ok=True)
    keys = read_keys(DATA)
    keys[PASSWORD_KEY] = password
    write_keys(DATA, keys)
    SETTINGS.write_text(json.dumps({"host": host, "port": 993, "username": username}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Đã lưu mật khẩu trong kho DPAPI của tài khoản Windows hiện tại.")
    print("Có thể dùng công cụ list_admin_mail và read_admin_mail trong phiên Codex mới.")


if __name__ == "__main__":
    main()
