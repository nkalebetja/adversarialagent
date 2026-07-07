import json
import os
from datetime import datetime


class ConversationLogger:

    def __init__(self, session_id):
        # Now accepts the session_id from the DatabaseClient
        self.session_id = session_id
        self.start_time = datetime.utcnow().isoformat()
        self.messages = []

    def log(self, sender, message):
        entry = {
            "message_id": str(len(self.messages) + 1),
            "sender": sender,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.messages.append(entry)

    def save_local_json(self):
        """
        Renamed from 'save' to 'save_local_json' to match the call in ai_steps.py
        """
        session_data = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": datetime.utcnow().isoformat(),
            "messages": self.messages
        }

        # Ensure the directory exists
        log_dir = "logs/sessions"
        os.makedirs(log_dir, exist_ok=True)

        # The file is named after the unique database reference
        file_path = os.path.join(log_dir, f"{self.session_id}.json")

        with open(file_path, "w") as f:
            json.dump(session_data, f, indent=4)

        # Returning absolute path is safer for the 'os.path.exists' check in behave
        return os.path.abspath(file_path)