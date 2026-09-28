@app.post("/download")
def download():
    raw_body = request.get_data(as_text=True)

    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    # Fallback: extract YouTube URL directly from raw request
    if not url:
        match = re.search(
            r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s"\'{}]+',
            raw_body
        )
        if match:
            url = match.group(0)

    if not url:
        return jsonify({
            "error": "YouTube URL is required",
            "received_body": raw_body
        }), 400

    if not is_youtube_url(url):
        return jsonify({
            "error": "Please provide a valid YouTube URL"
        }), 400

    temp_dir = tempfile.mkdtemp()

    output_template = os.path.join(
        temp_dir,
        "%(title).100s.%(ext)s"
    )

    options = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                files = os.listdir(temp_dir)

                if not files:
                    return jsonify({
                        "error": "Download failed"
                    }), 500

                filename = os.path.join(temp_dir, files[0])

            safe_title = re.sub(
                r'[\\/*?:"<>|]',
                "",
                info.get("title", "video")
            )

            return send_file(
                filename,
                as_attachment=True,
                download_name=f"{safe_title}.mp4",
                mimetype="video/mp4"
            )

    except Exception as e:
        return jsonify({
            "error": "Unable to download this video",
            "details": str(e)
        }), 500
