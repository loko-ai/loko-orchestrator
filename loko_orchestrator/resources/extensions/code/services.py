from flask import Flask, request, jsonify

app = Flask("")


@app.route("/", methods=["POST"])
def test():
    return jsonify(dict(msg="Hello extensions!"))


@app.route("/files", methods=["POST"])
def test2():
    return jsonify(dict(msg="Hello extensions!"))


if __name__ == "__main__":
    app.run("0.0.0.0", 8080)
