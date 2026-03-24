#!/bin/bash
set -euo pipefail

VIDEO=/root/lecture-recording.mp4
FRAME_DIR=/root/slide_gallery_assets
OUTPUT_HTML=/root/slide_gallery.html

mkdir -p "$FRAME_DIR"

ffmpeg -y -i "$VIDEO" -vf "select='eq(pict_type,I)'" -vsync vfr -q:v 2 "$FRAME_DIR/slide_%03d.jpg"

python3 <<'PY'
from pathlib import Path
import html

frame_dir = Path("/root/slide_gallery_assets")
output_html = Path("/root/slide_gallery.html")
frames = sorted(frame_dir.glob("slide_*.jpg"))

cards = []
for index, frame in enumerate(frames, start=1):
    filename = frame.name
    rel_path = f"slide_gallery_assets/{filename}"
    cards.append(
        "      <figure class=\"slide-card\" data-sequence=\"{index}\">\n"
        "        <img src=\"{src}\" alt=\"{alt}\">\n"
        "        <figcaption>{caption}</figcaption>\n"
        "      </figure>".format(
            index=index,
            src=html.escape(rel_path, quote=True),
            alt=html.escape(filename, quote=True),
            caption=html.escape(filename),
        )
    )

document = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Lecture Slide Gallery</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: Georgia, "Times New Roman", serif;
        background: #f4efe7;
        color: #1f1a17;
      }}
      body {{
        margin: 0;
        padding: 32px;
        background:
          radial-gradient(circle at top left, #fff7d8 0, transparent 28%),
          linear-gradient(180deg, #f7f1df 0%, #efe5d2 100%);
      }}
      main {{
        max-width: 1200px;
        margin: 0 auto;
      }}
      h1 {{
        margin: 0 0 12px;
        font-size: 2.4rem;
      }}
      p {{
        margin: 0 0 28px;
        font-size: 1rem;
      }}
      .gallery {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 20px;
      }}
      .slide-card {{
        margin: 0;
        padding: 14px;
        border: 1px solid #c7bca5;
        border-radius: 14px;
        background: rgba(255, 252, 245, 0.92);
        box-shadow: 0 10px 24px rgba(73, 52, 28, 0.12);
      }}
      .slide-card img {{
        display: block;
        width: 100%;
        height: auto;
        border-radius: 10px;
      }}
      .slide-card figcaption {{
        margin-top: 10px;
        font-family: "Courier New", monospace;
        font-size: 0.95rem;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>Lecture Slide Gallery</h1>
      <p>Source video: /root/lecture-recording.mp4</p>
      <section class="gallery">
{cards}
      </section>
    </main>
  </body>
</html>
""".format(cards="\n".join(cards))

output_html.write_text(document, encoding="utf-8")
PY
