from flask import (
    Flask,
    render_template,
    request,
    jsonify,
)

from assistant import process_user_input


app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/command", methods=["POST"])
def command():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    user_text = data.get("command", "")

    if not isinstance(user_text, str):
        return jsonify({
            "success": False,
            "message": "Command must be text."
        }), 400

    user_text = user_text.strip()

    if not user_text:
        return jsonify({
            "success": False,
            "message": "Command is empty."
        }), 400

    requested_provider = data.get("provider")

    if not isinstance(requested_provider, str):
        return jsonify({
            "success": False,
            "message": "Provider must be groq, deepseek, gemini, or local."
        }), 400

    requested_provider = requested_provider.strip().lower()

    if requested_provider not in {"groq", "deepseek", "gemini", "local"}:
        return jsonify({
            "success": False,
            "message": "Provider must be groq, deepseek, gemini, or local."
        }), 400

    try:
        response, effective_provider = process_user_input(
            user_text,
            provider=requested_provider,
            include_provider=True,
        )

        return jsonify({
            "success": True,
            "message": response,
            "provider": effective_provider,
        })

    except Exception as e:
        # Avoid exposing provider SDK error details or credentials in logs.
        print(f"Flask/Jarvis error: {type(e).__name__}")

        return jsonify({
            "success": False,
            "message": "Jarvis could not complete the request. Check that the selected model is available.",
            "provider": getattr(e, "effective_provider", requested_provider),
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
