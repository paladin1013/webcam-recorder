from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("video.html")


@app.route("/video")
def video():
    return app.send_static_file("recorded.mp4")


@app.route("/progress", methods=["POST"])
def progress():
    data = request.json
    print(f"Current video time: {data['time']} seconds")
    # Process the time data as needed
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(debug=True)
