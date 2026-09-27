"""
Laya Email Reader & Executive Briefing Manager
Supports:
- IMAP connection to Gmail, Outlook / Office365, Yahoo, iCloud, or custom IMAP servers
- Secure SSL connection with strict timeout (never hangs main loop)
- Unread & recent email fetching, sender, subject, date, and clean text snippet extraction
- AI / Executive briefing generation for JARVIS voice & UI readout
- Fallback guidance and webmail launcher if credentials are not yet set in .env
"""

import os
import email
from email.header import decode_header
import imaplib
import socket
import webbrowser
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class EmailManager:
    def __init__(self):
        self.user = os.getenv("EMAIL_USER", "").strip()
        self.password = os.getenv("EMAIL_PASSWORD", "").strip()
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "").strip()
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))

        # Autodetect common IMAP servers if not explicitly provided
        if not self.imap_server and self.user:
            lower = self.user.lower()
            if "gmail.com" in lower:
                self.imap_server = "imap.gmail.com"
            elif "outlook.com" in lower or "hotmail.com" in lower or "live.com" in lower:
                self.imap_server = "outlook.office365.com"
            elif "yahoo.com" in lower:
                self.imap_server = "imap.mail.yahoo.com"
            elif "icloud.com" in lower:
                self.imap_server = "imap.mail.me.com"

        self.last_emails: List[Dict[str, Any]] = []

    def is_configured(self) -> bool:
        return bool(self.user and self.password)

    def _decode_mime_words(self, s: str) -> str:
        if not s:
            return ""
        try:
            decoded_parts = decode_header(s)
            res = []
            for part, enc in decoded_parts:
                if isinstance(part, bytes):
                    try:
                        res.append(part.decode(enc or "utf-8", errors="replace"))
                    except Exception:
                        res.append(part.decode("latin-1", errors="replace"))
                else:
                    res.append(str(part))
            return "".join(res)
        except Exception:
            return str(s)

    def _extract_body_snippet(self, msg: email.message.Message, max_chars: int = 140) -> str:
        snippet = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            snippet = payload.decode("utf-8", errors="replace").strip()
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    snippet = payload.decode("utf-8", errors="replace").strip()
        except Exception:
            pass

        # Clean up whitespace and newlines
        snippet = " ".join(snippet.split())
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars].rstrip() + "..."
        return snippet

    def check_emails(self, limit: int = 5, unread_only: bool = True) -> Dict[str, Any]:
        """
        Connects via IMAP and retrieves recent or unread emails.
        Returns a dict with status, emails list, and executive summary.
        """
        if not self.is_configured():
            return {
                "status": "not_configured",
                "count": 0,
                "emails": [],
                "summary": "Email account is not configured yet. Add EMAIL_USER and EMAIL_PASSWORD (App Password) into .env to enable live email synchronization.",
                "spoken": "Your email credentials are not configured yet, sir. You can add your email and app password in the configuration file."
            }

        server_host = self.imap_server or "imap.gmail.com"
        socket.setdefaulttimeout(5.0)

        try:
            mail = imaplib.IMAP4_SSL(server_host, self.imap_port, timeout=5.0)
            mail.login(self.user, self.password)
            mail.select("INBOX", readonly=True)

            search_criteria = "UNSEEN" if unread_only else "ALL"
            status, response = mail.search(None, search_criteria)

            if status != "OK":
                mail.logout()
                return {
                    "status": "error",
                    "count": 0,
                    "emails": [],
                    "summary": f"Could not query INBOX with criteria '{search_criteria}'.",
                    "spoken": "I was unable to query your inbox at this time."
                }

            email_ids = response[0].split()
            total_found = len(email_ids)

            if total_found == 0 and unread_only:
                # Also check recent all if 0 unread
                status, response = mail.search(None, "ALL")
                all_ids = response[0].split()
                mail.logout()
                return {
                    "status": "ok",
                    "count": 0,
                    "total_inbox": len(all_ids),
                    "emails": [],
                    "summary": f"You have 0 unread emails. Total messages in inbox: {len(all_ids)}.",
                    "spoken": "You have zero unread emails in your inbox, sir. All caught up."
                }

            # Get the latest `limit` IDs
            target_ids = email_ids[-limit:]
            target_ids.reverse()

            fetched_emails = []
            for eid in target_ids:
                res, data = mail.fetch(eid, "(RFC822.HEADER BODY.PEEK[TEXT])")
                if res != "OK" or not data or not data[0]:
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = self._decode_mime_words(msg.get("Subject", "(No Subject)"))
                sender = self._decode_mime_words(msg.get("From", "Unknown Sender"))
                date_str = msg.get("Date", "")

                # Clean sender name
                sender_clean = sender
                if "<" in sender:
                    sender_clean = sender.split("<")[0].strip().replace('"', "")
                if not sender_clean:
                    sender_clean = sender

                snippet = self._extract_body_snippet(msg, max_chars=120)

                fetched_emails.append({
                    "id": eid.decode(),
                    "sender": sender_clean,
                    "raw_sender": sender,
                    "subject": subject,
                    "date": date_str,
                    "snippet": snippet
                })

            mail.logout()
            self.last_emails = fetched_emails

            # Build Executive Report
            summary_lines = [f"Found {total_found} unread email{'s' if total_found != 1 else ''}:"]
            spoken_parts = [f"You have {total_found} unread email{'s' if total_found != 1 else ''}, sir."]

            for idx, em in enumerate(fetched_emails, 1):
                summary_lines.append(f"{idx}. From {em['sender']}: '{em['subject']}'")
                if idx <= 3:
                    spoken_parts.append(f"Number {idx} from {em['sender']} regarding {em['subject']}.")

            summary_text = "\n".join(summary_lines)
            spoken_text = " ".join(spoken_parts)

            return {
                "status": "ok",
                "count": len(fetched_emails),
                "total_unread": total_found,
                "emails": fetched_emails,
                "summary": summary_text,
                "spoken": spoken_text
            }

        except imaplib.IMAP4.error as e:
            return {
                "status": "auth_error",
                "count": 0,
                "emails": [],
                "summary": f"IMAP Authentication failed: {e}. If using Gmail, make sure to generate an App Password.",
                "spoken": "Authentication failed for your email account. Please verify your app password."
            }
        except socket.timeout:
            return {
                "status": "timeout",
                "count": 0,
                "emails": [],
                "summary": f"Connection to {server_host} timed out after 5 seconds.",
                "spoken": "The email server connection timed out, sir."
            }
        except Exception as e:
            return {
                "status": "error",
                "count": 0,
                "emails": [],
                "summary": f"Failed checking emails: {e}",
                "spoken": f"An error occurred while checking emails: {str(e)[:40]}"
            }

    def open_webmail(self) -> str:
        """Opens the user's webmail in browser."""
        if self.user and "gmail" in self.user.lower():
            url = "https://mail.google.com"
        elif self.user and ("outlook" in self.user.lower() or "hotmail" in self.user.lower()):
            url = "https://outlook.live.com"
        else:
            url = "https://mail.google.com"
        webbrowser.open(url)
        return f"Opening webmail at {url}"


_email_manager_instance: Optional[EmailManager] = None

def get_email_manager() -> EmailManager:
    global _email_manager_instance
    if _email_manager_instance is None:
        _email_manager_instance = EmailManager()
    return _email_manager_instance
