let reportInterval;

const ws = new WebSocket('ws://' + window.location.host + '/ws');

ws.onmessage = function (event) {
    const data = JSON.parse(event.data);
    document.getElementById('client_ip').textContent = data.client_ip;
};
ws.onopen = () => {
    ws.send("Opened");
}

function updateVideoPlayer() {
    var selectedVideo = document.getElementById('videoList').value;
    var videoPlayer = document.getElementById('videoPlayer');
    var downloadLink = document.getElementById('downloadLink');
    var videoURL = '/recordings/' + selectedVideo;
    videoPlayer.src = videoURL;
    videoPlayer.load();
    downloadLink.href = videoURL;
}

function reportTime() {
    var video = document.getElementById('videoPlayer');
    var time = video.currentTime;
    // Get the current timestamp of the web client and convert to seconds (float)
    var client_timestamp = new Date().getTime() / 1000;

    fetch('/progress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },

        // Return the time in the body of the response as well as whether the video is paused
        body: JSON.stringify({
            'time': time,
            'paused': video.paused,
            'client_timestamp': client_timestamp,
        }),
    });
}

function setupVideo() {
    var video = document.getElementById('videoPlayer');
    if (video) {
        // video.ontimeupdate = reportTime;
        if (reportInterval) {
            clearInterval(reportInterval);
        }
        reportInterval = setInterval(reportTime, 200); // Report every 200ms
    }
}


window.onload = function () {
    setupVideo();
    updateVideoPlayer(); // Set the initial video
};
window.onunload = function () {
    ws.send("Closed");
    clearInterval(reportInterval);
};
