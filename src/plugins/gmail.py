# src/plugins/gmail.py

from .base import PublishPlugin, Entry
from typing import Iterator

class Plugin(PublishPlugin):
    """
    A mock publisher plugin that "sends" entries via Gmail.

    Instead of calling the real Gmail API, it formats the entry
    content into an email format and prints it to the console.
    """
    def __init__(self, config: dict):
        super().__init__(config)
        self.validate_config()
        print(f"Executing GmailPlugin (mock): Emails will be printed to console.")

    def validate_config(self):
        """Validates the plugin-specific configuration."""
        if 'recipient' not in self.config:
            raise ValueError("Config for Gmail plugin must contain a 'recipient'.")

    @property
    def name(self) -> str:
        return "Publish::Gmail"

    def execute(self, entries: Iterator[Entry]) -> None:
        """
        Processes each entry and prints a mock email.
        """
        recipient = self.config.get('recipient')
        count = 0
        for entry in entries:
            self.send_mock_email(entry, recipient)
            count += 1

        print(f"GmailPlugin: Processed {count} entries.")

    def send_mock_email(self, entry: Entry, recipient: str):
        """
        Formats and prints the mock email to the console.
        """
        subject = f"RAG Idea from Source: {entry.source}"
        body = f"ID: {entry.id}\n"
        body += f"Timestamp: {entry.timestamp}\n\n"
        body += f"Content:\n{entry.content}\n\n"
        body += f"Metadata:\n{entry.metadata}\n"

        print("--- MOCK GMAIL SEND ---")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print("-----------------------")
        print(body)
        print("--- END MOCK GMAIL ---\n")
