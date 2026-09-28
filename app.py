from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import tempfile
import os
import re
import json

app = Flask(__name__)
CORS(app)

YOUTUBE_DOMAINS = (
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
)


def is_youtube_url(url):
    url = url.lower().strip()
    return any(domain in url for domain in YOUTUBE_DOMAINS)


@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "service": "YouTube Downloader API"
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "ok"
    })


@app.post("/download")
def download():

    # Read the raw request body
    raw_body = request.get_data(as_text=True)

    url = ""

    # Try JSON parsing
    try:
        data = json.loads(raw_body)

        if isinstance(data, dict):
            url = str(data.get("url", "")).strip()

    except Exception:
        pass

    # Try Flask JSON parser
    if not url:

        try:
            data = request.get_json(silent=True)

            if isinstance(data, dict):
                url = str(data.get("url", "")).strip()

        except Exception:
            pass

    # Try extracting a YouTube URL directly from the body
    if not url:

        match = re.search(
            r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s"\'<>]+',
            raw_body
        )

        if match:
            url = match.group(0)

    # URL missing
    if not url:

        return jsonify({
            "error": "YouTube URL is required",
            "received_body": raw_body,
            "received_content_type": request.content_type
        }), 400

    # Validate YouTube URL
    if not is_youtube_url(url):

        return jsonify({
            "error": "Please provide a valid YouTube URL"
        }), 400

    # Temporary directory
    temp_dir = tempfile.mkdtemp()

    output_template = os.path.join(
        temp_dir,
        "%(title).100s.%(ext)s"
    )

    # yt-dlp settings
    options = {
        "format": "best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": False,
        "restrictfilenames": True,
    }

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            filename = ydl.prepare_filename(info)

            # If the expected filename doesn't exist,
            # find the downloaded file
            if not os.path.exists(filename):

                files = os.listdir(temp_dir)

                if not files:

                    return jsonify({
                        "error": "Download failed",
                        "details": "yt-dlp did not create a file"
                    }), 500

                filename = os.path.join(
                    temp_dir,
                    files[0]
                )

            safe_title = re.sub(
                r'[\\/*?:"<>|]',
                "",
                info.get("title", "video")
            )

            # Determine the actual extension
            extension = os.path.splitext(filename)[1].lower()

            # Send the downloaded file
            return send_file(
                filename,
                as_attachment=True,
                download_name=f"{safe_title}{extension}",
                mimetype="video/mp4"
            )

    except Exception as e:

        return jsonify({
            "error": "Unable to download this video",
            "details": str(e)
        }), 500


if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
