"""Slack publisher for posting changelogs to Slack channels."""

import requests
from typing import Optional


class SlackPublisher:
    """Publisher for sending changelogs to Slack."""

    def __init__(self, webhook_url: str, channel: Optional[str] = None):
        """
        Initialize Slack publisher.

        Args:
            webhook_url: Slack webhook URL
            channel: Optional channel override (e.g., '#changelog')
        """
        self.webhook_url = webhook_url
        self.channel = channel

    def _chunk_message(self, text: str, max_length: int = 3900) -> list:
        """
        Split message into chunks if it exceeds Slack's size limit.

        Args:
            text: Message text
            max_length: Maximum length per message chunk

        Returns:
            List of message chunks
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_length = 0

        for line in lines:
            line_length = len(line) + 1  # +1 for newline

            if current_length + line_length > max_length:
                # Save current chunk and start new one
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length

        # Add remaining lines
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def publish(self, changelog_text: str, dry_run: bool = False) -> bool:
        """
        Publish changelog to Slack.

        Args:
            changelog_text: Formatted changelog text
            dry_run: If True, print to console instead of sending

        Returns:
            True if successful, False otherwise
        """
        if dry_run:
            print("=== DRY RUN MODE ===")
            print("Would post to Slack:")
            print(changelog_text)
            return True

        # Split into chunks if needed
        chunks = self._chunk_message(changelog_text)

        for i, chunk in enumerate(chunks):
            payload = {"text": chunk}

            if self.channel:
                payload["channel"] = self.channel

            # Add part indicator for multi-part messages
            if len(chunks) > 1:
                payload["text"] = f"[Part {i+1}/{len(chunks)}]\n\n{chunk}"

            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()

                if response.text != "ok":
                    print(f"Unexpected response from Slack: {response.text}")
                    return False

            except requests.exceptions.RequestException as e:
                print(f"Error posting to Slack: {e}")
                return False

        print(f"Successfully posted changelog to Slack ({len(chunks)} message(s))")
        return True

    def publish_from_file(self, file_path: str, dry_run: bool = False) -> bool:
        """
        Read changelog from file and publish to Slack.

        Args:
            file_path: Path to changelog markdown file
            dry_run: If True, print to console instead of sending

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                changelog_text = f.read()

            return self.publish(changelog_text, dry_run)

        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            return False
        except Exception as e:
            print(f"Error reading file: {e}")
            return False
