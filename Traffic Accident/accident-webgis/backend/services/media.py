import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from backend.models import AccidentMedia

logger = logging.getLogger("AccidentMedia")
MEDIA_DIR = Path(
    os.getenv(
        "ACCIDENT_MEDIA_DIR",
        Path(__file__).resolve().parents[1] / "uploads",
    )
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_SIGNATURES = {
    "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP"),
}


def store_tweet_image(image_url: str, storage_dir: Path = MEDIA_DIR) -> str:
    parsed_url = urlparse(image_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "pbs.twimg.com":
        raise ValueError("Only HTTPS images hosted on pbs.twimg.com are allowed")

    request = Request(
        image_url,
        headers={"User-Agent": "AccidentWebGIS/1.0", "Accept": "image/*"},
    )
    with urlopen(request, timeout=12) as response:
        final_url = response.geturl() if hasattr(response, "geturl") else image_url
        if urlparse(final_url).hostname != "pbs.twimg.com":
            raise ValueError("Tweet image redirected away from pbs.twimg.com")
        content_type = response.headers.get_content_type().lower()
        image_bytes = response.read(MAX_IMAGE_BYTES + 1)

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("Tweet image exceeds the 10 MB limit")

    image_format = IMAGE_SIGNATURES.get(content_type)
    if not image_format or not image_format[1](image_bytes):
        raise ValueError("Tweet attachment is not a supported image")

    storage_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{uuid.uuid4().hex}{image_format[0]}"
    (storage_dir / file_name).write_bytes(image_bytes)
    return f"/media/{file_name}"


def persist_tweet_media(
    db: Session,
    accident_id: int,
    media_items: Iterable[Dict[str, Any]],
) -> int:
    saved_count = 0
    for item in media_items:
        source_url = (item.get("url") or "").strip()
        if not source_url:
            continue

        exists = (
            db.query(AccidentMedia)
            .filter_by(accident_id=accident_id, source_url=source_url)
            .first()
        )
        if exists:
            continue

        try:
            media_url = store_tweet_image(source_url)
        except Exception as error:
            logger.warning("Failed to store tweet image for accident %s: %s", accident_id, error)
            continue

        db.add(AccidentMedia(
            accident_id=accident_id,
            media_url=media_url,
            source_url=source_url,
            alt_text=(item.get("alt_text") or "")[:1000],
        ))
        saved_count += 1

    if saved_count:
        db.commit()
    return saved_count