from flask import (
    Flask,
    render_template,
    request,
    jsonify,
)


app = Flask(__name__)


@app.route("/")
def home():

    return render_template(
        "index.html"
    )


@app.route(
    "/command",
    methods=["POST"]
)
def command():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        })


    user_text = data.get(
        "command",
        ""
    ).strip()


    if not user_text:

        return jsonify({
            "success": False,
            "message": "Command is empty."
        })


    return jsonify({
        "success": True,
        "message": f"Received: {user_text}"
    })


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )