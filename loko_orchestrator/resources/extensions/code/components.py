from flask import Flask, request, jsonify

app = Flask("")


@app.route("/", methods=["POST"])
def test():
    return jsonify(dict(msg="Hello extensions!"))


app.run("0.0.0.0", 8080)
