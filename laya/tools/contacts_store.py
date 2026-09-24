"""
Laya Local Contact & Address Book Store
Stores and manages user contacts (phone, Telegram username, notes) locally
with instant fuzzy matching and persistent JSON storage.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class ContactsStore:
    _instance: Optional["ContactsStore"] = None

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_file = Path(storage_path)
        else:
            base_dir = Path.home() / ".laya"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.storage_file = base_dir / "contacts.json"

        self.contacts: Dict[str, Dict[str, Any]] = {}
        self._load()

    @classmethod
    def get_instance(cls) -> "ContactsStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.contacts = json.load(f)
            except Exception:
                self.contacts = {}
        else:
            # Seed with common aliases if empty
            self.contacts = {}
            self._save()

    def _save(self):
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.contacts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ContactsStore] Save error: {e}")

    def save_contact(
        self,
        name: str,
        phone: str = "",
        telegram: str = "",
        whatsapp: str = "",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Add or update a contact."""
        key = name.lower().strip()
        if not key:
            return {"error": "Contact name cannot be empty."}

        clean_tg = telegram.lstrip("@").strip()
        clean_phone = re.sub(r"[^\d+]", "", phone.strip())
        clean_wa = re.sub(r"[^\d+]", "", whatsapp.strip()) or clean_phone

        record = {
            "name": name.strip(),
            "phone": clean_phone,
            "telegram": clean_tg,
            "whatsapp": clean_wa,
            "notes": notes.strip(),
        }

        self.contacts[key] = record
        self._save()
        return record

    def get_contact(self, query: str) -> Optional[Dict[str, Any]]:
        """Find a contact by exact or partial name/alias."""
        q = query.lower().strip()
        if not q:
            return None

        # Exact match
        if q in self.contacts:
            return self.contacts[q]

        # Substring / partial match
        for key, record in self.contacts.items():
            if q == key or q in key or key in q:
                return record
            if q == record.get("telegram", "").lower():
                return record

        return None

    def search_contacts(self, query: str) -> List[Dict[str, Any]]:
        """Search contacts matching query."""
        q = query.lower().strip()
        results = []
        for key, record in self.contacts.items():
            if q in key or q in record.get("phone", "") or q in record.get("telegram", "").lower():
                results.append(record)
        return results

    def list_contacts(self) -> List[Dict[str, Any]]:
        """Return all contacts."""
        return list(self.contacts.values())

    def delete_contact(self, name: str) -> bool:
        """Remove a contact."""
        key = name.lower().strip()
        if key in self.contacts:
            del self.contacts[key]
            self._save()
            return True
        return False


def get_contacts_store() -> ContactsStore:
    return ContactsStore.get_instance()
