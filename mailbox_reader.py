"""Read-only IMAP access for the owner's admin mailbox.

The password lives in the existing Windows DPAPI key vault, never in this file.
"""
from __future__ import annotations

import imaplib
import json
import re
import ssl
from contextlib import contextmanager
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path

from key_store import resolve_key


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SETTINGS = DATA / "mailbox.json"
PASSWORD_KEY = "VUHOCAI_ADMIN_IMAP_PASSWORD"
MAX_MESSAGE_BYTES = 1_000_000
MAX_BODY_CHARS = 12_000


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return " ".join(" ".join(self.parts).split())


def _decode(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(str(value))))
    except (LookupError, UnicodeError):
        return str(value)


def _settings():
    if not SETTINGS.is_file():
        raise ValueError("Chưa cấu hình mailbox. Chạy CONFIGURE_MAIL.cmd trên PC.")
    value = json.loads(SETTINGS.read_text(encoding="utf-8"))
    host = value.get("host")
    username = value.get("username")
    port = value.get("port", 993)
    if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host):
        raise ValueError("IMAP host không hợp lệ.")
    if not isinstance(username, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+", username):
        raise ValueError("IMAP username không hợp lệ.")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("IMAP port không hợp lệ.")
    return host, port, username


@contextmanager
def _inbox():
    host, port, username = _settings()
    password = resolve_key(DATA, PASSWORD_KEY)
    connection = imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context(), timeout=15)
    try:
        connection.login(username, password)
        status, _ = connection.select("INBOX", readonly=True)
        if status != "OK":
            raise RuntimeError("Không mở được INBOX ở chế độ chỉ đọc.")
        yield connection
    finally:
        try:
            connection.logout()
        except (OSError, imaplib.IMAP4.error):
            pass


def _uid(value):
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,18}", value):
        raise ValueError("UID thư phải là số nguyên dương.")
    return value


def _headers(message, uid):
    return {
        "uid": uid,
        "from": _decode(message.get("From")),
        "to": _decode(message.get("To")),
        "date": str(message.get("Date", "")),
        "subject": _decode(message.get("Subject")),
    }


def _payload(data):
    for item in data or []:
        if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes):
            return item[1]
    raise RuntimeError("Máy chủ IMAP không trả về nội dung thư.")


def list_mail(limit=20, unread_only=False):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("limit phải từ 1 đến 50.")
    if not isinstance(unread_only, bool):
        raise ValueError("unread_only phải là true hoặc false.")
    with _inbox() as connection:
        status, result = connection.uid("SEARCH", None, "UNSEEN" if unread_only else "ALL")
        if status != "OK":
            raise RuntimeError("Không lấy được danh sách UID.")
        uids = result[0].split()[-limit:][::-1] if result and result[0] else []
        messages = []
        for uid in uids:
            status, data = connection.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM TO DATE SUBJECT)])")
            if status != "OK":
                continue
            message = BytesParser(policy=policy.default).parsebytes(_payload(data))
            messages.append(_headers(message, uid.decode("ascii")))
        return {"mailbox": "INBOX", "messages": messages}


def read_mail(uid):
    uid = _uid(uid)
    with _inbox() as connection:
        status, data = connection.uid("FETCH", uid, "(RFC822.SIZE)")
        if status != "OK" or not data:
            raise ValueError("Không tìm thấy thư với UID này.")
        size_line = next((item for item in data if isinstance(item, bytes)), b"")
        match = re.search(rb"RFC822\.SIZE (\d+)", size_line)
        if not match:
            raise RuntimeError("Không xác định được kích thước thư.")
        size = int(match.group(1))
        if size > MAX_MESSAGE_BYTES:
            raise ValueError("Thư vượt giới hạn 1 MB; hãy mở bằng Thunderbird.")
        status, data = connection.uid("FETCH", uid, "(BODY.PEEK[])")
        if status != "OK":
            raise ValueError("Không tìm thấy thư với UID này.")
        message = BytesParser(policy=policy.default).parsebytes(_payload(data))
        body = message.get_body(preferencelist=("plain", "html")) if message.is_multipart() else message
        content = body.get_content() if body else ""
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        if body and body.get_content_type() == "text/html":
            parser = _PlainText()
            parser.feed(content)
            content = parser.text()
        attachments = [
            {"filename": _decode(part.get_filename()), "content_type": part.get_content_type()}
            for part in message.walk()
            if part.get_content_disposition() == "attachment"
        ]
        return {**_headers(message, uid), "body": str(content)[:MAX_BODY_CHARS],
                "body_truncated": len(str(content)) > MAX_BODY_CHARS,
                "attachments": attachments}
