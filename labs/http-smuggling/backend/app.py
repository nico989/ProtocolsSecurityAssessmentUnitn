from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="[backend] %(message)s")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    app.logger.warning(
        "!! /admin accessed — method=%s cookie=%s",
        request.method,
        request.headers.get("Cookie", "(none)"),
    )
    return jsonify({
        "page": "ADMIN PANEL",
        "flag": "flag{cl_te_smuggling_success}",
        "note": "Only reachable via request smuggling.",
        "incoming_headers": dict(request.headers),
    })



@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/<path:path>",             methods=["GET", "POST", "PUT", "DELETE"])
def catch_all(path):
    return jsonify({
        "method": request.method,
        "path": f"/{path}",
        "headers": dict(request.headers),
        "body": request.get_data(as_text=True),
    })
