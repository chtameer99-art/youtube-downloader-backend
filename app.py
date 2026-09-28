from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import tempfile
import os
import re
import glob

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
    try:
        url_lower = url.lower()
        return any(domain in url_lower for domain in YOUTUBE_DOMAINS)
    except Exception:
        return False


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
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be JSON"
        }), 400

    url = str(data.get("url", "")).strip()

    if not url:
        return jsonify({
            "error": "YouTube URL is required"
        }), 400

    if not is_youtube_url(url):
        return jsonify({
            "error": "Please provide a valid YouTube URL"
        }), 400

    temp_dir = tempfile.mkdtemp(prefix="youtube_")

    output_template = os.path.join(
        temp_dir,
        "%(title).100s.%(ext)s"
    )

    options = {
        # Best available video + audio.
        # If separate streams are unavailable,
        # fall back to the best single file.
        "format": "bv*+ba/b",

        # Merge separate video/audio into MP4.
        "merge_output_format": "mp4",

        "outtmpl": output_template,

        "noplaylist": True,

        "quiet": True,
        "no_warnings": True,

        "restrictfilenames": True,

        # Helps yt-dlp choose downloadable formats.
        "check_formats": True,

        # Don't download subtitles, thumbnails, etc.
        "writesubtitles": False,
        "writeautomaticsub": False,
        "writethumbnail": False,

        # Use ffmpeg installed on Render.
        "postprocessors": [],
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            title = info.get("title", "video")

            safe_title = re.sub(
                r'[\\/*?:"<>|]',
                "",
                title
            ).strip()

            if not safe_title:
                safe_title = "video"

            # Find downloaded files.
            files = []

            for path in glob.glob(
                os.path.join(temp_dir, "*")
            ):
                if os.path.isfile(path):
                    files.append(path)

            if not files:
                return jsonify({
                    "error": "Download completed but no file was created"
                }), 500

            # Prefer MP4.
            mp4_files = [
                f for f in files
                if f.lower().endswith(".mp4")
            ]

            if mp4_files:
                filename = mp4_files[0]
            else:
                filename = files[0]

            extension = os.path.splitext(filename)[1].lower()

            # If yt-dlp produced a non-mp4 file,
            # send it with its real extension.
            download_name = safe_title + extension

            return send_file(
                filename,
                as_attachment=True,
                download_name=download_name,
                mimetype="video/mp4"
                if extension == ".mp4"
                else "application/octet-stream"
            )

    except yt_dlp.utils.DownloadError as e:

        return jsonify({
            "error": "Unable to download this YouTube video",
            "details": str(e)
        }), 500

    except Exception as e:

        return jsonify({
            "error": "Server error",
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
