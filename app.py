from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/whatsapp/message", methods=["POST"])
def whatsapp_message():
    data = request.get_json(silent=True)

    print("Received payload:", data)

    if not data:
        return jsonify({
            "status": "failed",
            "reason": "No JSON payload received"
        }), 400

    messages = data.get("Messages", [])

    if not messages:
        return jsonify({
            "status": "failed",
            "reason": "No Messages found in payload"
        }), 400

    first_message = messages[0]
    content = first_message.get("Content")
    sender = first_message.get("From")
    receiver = first_message.get("To")

    print(f"Message from {sender} to {receiver}: {content}")

    return jsonify({
        "status": "received",
        "message": content,
        "from": sender,
        "to": receiver
    }), 200