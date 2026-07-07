import os
import requests
import threading
import logging
from flask import Flask, request, jsonify
from queue import Queue, Empty


class WhatsAppClient:
    # Shared Flask server so it does not start again for every scenario
    _app = None
    _server_started = False
    _clients_by_phone = {}

    def __init__(self, phone, webhook_port=5000):
        self.phone = phone
        self.webhook_port = int(os.getenv("WEBHOOK_PORT", webhook_port))

        self.api_url = os.getenv(
            "POLICY_PILOT_API_URL",
            "https://policy-pilot-qaEdgar.mobilitysystems.cloud/api/whatsapp/message"
        )

        self.integration_id = os.getenv(
            "POLICY_PILOT_INTEGRATION_ID",
            "01KPDN4BC9XREHQ3P5S5A4R5NB"
        )

        self.message_queue = Queue()

        # Register this client by phone number
        WhatsAppClient._clients_by_phone[self.phone] = self

        # Start Flask only once
        if not WhatsAppClient._server_started:
            WhatsAppClient._app = Flask(__name__)
            self.setup_routes(WhatsAppClient._app)

            server_thread = threading.Thread(
                target=self.run_server,
                args=(self.webhook_port,),
                daemon=True
            )
            server_thread.start()

            WhatsAppClient._server_started = True

            print(f"Webhook server started on port {self.webhook_port}")
            print(f"Local webhook URL: http://localhost:{self.webhook_port}/webhook")
            print("If using ngrok, expose it with:")
            print(f"ngrok http {self.webhook_port}")
        else:
            print(f"Webhook server already running on port {self.webhook_port}")

        print(f"WhatsAppClient initialized for phone: {self.phone}")

    @classmethod
    def setup_routes(cls, app):
        @app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "ok"}), 200

        @app.route("/webhook", methods=["POST"])
        def receive_message():
            data = request.get_json(silent=True)

            print(f"Webhook received payload: {data}")

            if not data:
                return jsonify({"status": "ignored", "reason": "empty payload"}), 200

            # Try different possible field names because webhook payloads are not always consistent
            sent_to = (
                data.get("sent_to")
                or data.get("SentTo")
                or data.get("to")
                or data.get("To")
            )

            msg_content = (
                data.get("message")
                or data.get("Message")
                or data.get("content")
                or data.get("Content")
                or ""
            )

            suggestions = (
                data.get("message_suggestion")
                or data.get("MessageSuggestion")
                or data.get("suggestions")
                or data.get("Suggestions")
            )

            # If ICE sends a nested Messages array
            if not msg_content and isinstance(data.get("Messages"), list) and data["Messages"]:
                first_msg = data["Messages"][0]
                sent_to = sent_to or first_msg.get("To") or first_msg.get("to")
                msg_content = first_msg.get("Content") or first_msg.get("content") or ""

            # Find correct client
            client = cls._clients_by_phone.get(sent_to)

            # Fallback: if sent_to is missing, use the first registered client
            if client is None and len(cls._clients_by_phone) == 1:
                client = list(cls._clients_by_phone.values())[0]

            if client is None:
                print(f"No matching client found for sent_to: {sent_to}")
                return jsonify({
                    "status": "ignored",
                    "reason": f"no client registered for {sent_to}"
                }), 200

            if msg_content:
                print(f"Bot response received for {client.phone}: {msg_content}")
                client.message_queue.put(msg_content)
            else:
                print("Webhook received but no message content was found.")

            if suggestions:
                client.send_confirmation("YesConfirmation")

            return jsonify({"status": "received"}), 200

    def run_server(self, port):
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        # host="0.0.0.0" is important when hosting on a server/Azure
        WhatsAppClient._app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False
        )

    def send_message(self, message):
        print(f"Sending via API: {message}")

        payload = {
            "Messages": [
                {
                    "Channel": "Adversarial",
                    "Content": message,
                    "From": self.phone,
                    "To": "AdAgentOne",
                    "IntegrationId": None
                }
            ],
            "IsSuggestion": False,
            "IsViolation": False
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            print(f"Send response status: {response.status_code}")
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Failed to send message via API. Error: {e}")
            return None

    def send_confirmation(self, confirmation_type):
        print(f"Auto-replying with Confirmation: {confirmation_type}")

        payload = {
            "Messages": [
                {
                    "Channel": "Adversarial",
                    "Content": confirmation_type,
                    "From": self.phone,
                    "To": "AdAgentOne",
                    "IntegrationId": self.integration_id,
                    "PostbackData": confirmation_type
                }
            ],
            "IsSuggestion": True,
            "IsViolation": False
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            print(f"Confirmation response status: {response.status_code}")
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Failed to send confirmation via API. Error: {e}")
            return None

    def read_response_with_timeout(self, timeout=120):
        print(f"Waiting for webhook response from ICE, max {timeout}s...")

        try:
            return self.message_queue.get(timeout=timeout)
        except Empty:
            print("Timeout reached: Bot did not respond via webhook.")
            print("Check that ICE callback URL points to your public webhook URL.")
            print(f"Expected local route: /webhook on port {self.webhook_port}")
            return None