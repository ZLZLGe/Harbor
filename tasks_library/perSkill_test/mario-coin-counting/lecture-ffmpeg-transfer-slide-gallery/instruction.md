You are organizing a lecture slide review page from the classroom recording stored at `/root/lecture-recording.mp4`.

Requirements:

1. Extract every key frame from the video in timeline order and save them under `/root/slide_gallery_assets/` using the exact filename pattern `slide_%03d.jpg`.
2. Create `/root/slide_gallery.html` as a complete HTML document.
3. The HTML document must contain the exact page title `Lecture Slide Gallery`.
4. The visible page heading must contain the exact text `Lecture Slide Gallery`.
5. The page must include one gallery card per extracted image, in timeline order.
6. Each gallery card must be a `<figure>` element with class `slide-card` and a `data-sequence` attribute starting at `1` and increasing by `1`.
7. Inside each gallery card, include:
   - one `<img>` element whose `src` is the relative path `slide_gallery_assets/slide_%03d.jpg`
   - an `alt` attribute equal to the image filename, such as `slide_001.jpg`
   - one `<figcaption>` whose visible text is exactly the same filename
8. Do not skip any extracted key frames, and do not add extra gallery cards.

The final HTML should be directly viewable in a browser by opening `/root/slide_gallery.html`.
