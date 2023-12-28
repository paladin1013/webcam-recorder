from quart import Quart, render_template, request, jsonify

app = Quart(__name__)


@app.route("/")
async def index():
    return await render_template("video.html")


@app.route("/video")
async def video():
    return await app.send_static_file("recorded.mp4")


@app.route("/progress", methods=["POST"])
async def progress():
    data = await request.get_json()
    print(f"Current video time: {data['time']} seconds")
    # Process the time data as needed
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(debug=True)
