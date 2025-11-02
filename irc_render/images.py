"""Image helpers for inline rendering."""

from __future__ import annotations

import io
import logging
import re
import urllib.request
from typing import Optional
from urllib.parse import urlparse

from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

URL_RE = re.compile(r"(https?://\S+)")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")


def looks_like_image_url(url: str) -> bool:
    try:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in IMAGE_EXTS)
    except Exception as exc:  # pragma: no cover - very unlikely
        logger.debug("failed to inspect url path %s: %s", url, exc)
        return False


def download_image_bytes(
    url: str,
    max_bytes: int = 5 * 1024 * 1024,
    timeout: int = 7,
) -> Optional[bytes]:
    """Download up to max_bytes from url. Returns bytes or None on failure."""
    logger.info(f"downloading image {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "irc-log-pdf/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                logger.info(
                    "skipping %s: content-length %s exceeds limit %d",
                    url,
                    content_length,
                    max_bytes,
                )
                return None
            data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                logger.info("skipping %s: response exceeded byte limit", url)
                return None
            logger.debug("downloaded %s (%d bytes)", url, len(data))
            return data
    except Exception as exc:
        logger.info("failed to download %s: %s", url, exc)
        return None


def load_image_reader(data: bytes) -> tuple[ImageReader, tuple[int, int]]:
    """Create a ReportLab ImageReader and return it with pixel dimensions."""
    bio = io.BytesIO(data)
    img = ImageReader(bio)
    size = img.getSize()
    logger.debug("loaded image (%d x %d)", size[0], size[1])
    return img, size
