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

    user_text = data.get("command", "").strip()

    if not user_text:
        return jsonify({
            "success": False,
            "message": "Command is empty."
        }), 400

    try:
        response = process_user_input(user_text)

        return jsonify({
            "success": True,
            "message": response
        })

    except Exception as e:
        print(f"Flask/Jarvis error: {e}")

        return jsonify({
            "success": False,
            "message": "Jarvis encountered an error."
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )