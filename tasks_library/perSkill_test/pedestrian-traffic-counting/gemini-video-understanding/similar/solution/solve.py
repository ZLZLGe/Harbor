import json
from openpyxl import Workbook

INPUT_PATH = "/root/video_tracks.json"
OUTPUT_PATH = "/root/similar_count.xlsx"


def main() -> None:
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    rows = []
    for video in payload.get("videos", []):
        filename = video["filename"]
        unique_ids = set()
        for track in video.get("tracks", []):
            if track.get("label") == "pedestrian":
                unique_ids.add(track.get("track_id"))
        rows.append((filename, len(unique_ids)))

    rows.sort(key=lambda item: item[0])

    wb = Workbook()
    ws = wb.active
    ws.title = "results"
    ws.append(["filename", "number"])
    for filename, number in rows:
        ws.append([filename, number])
    wb.save(OUTPUT_PATH)


if __name__ == "__main__":
    main()
