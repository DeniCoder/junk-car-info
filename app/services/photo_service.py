import hashlib
import io
import os
import struct

from PIL import Image, ImageOps
from flask import current_app

from app.storage.local_storage import LocalStorage

ALLOWED_MAGIC = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG": "png",
    b"RIFF": "webp",
}

MAX_PIXELS = 50_000_000


def get_storage():
    return LocalStorage(current_app.config["MEDIA_ROOT"])


def check_magic_bytes(data):
    header = data[:16]
    for magic, fmt in ALLOWED_MAGIC.items():
        if header.startswith(magic):
            if fmt == "webp":
                if b"WEBP" in header:
                    return fmt
                continue
            return fmt
    return None


def strip_exif(img):
    return ImageOps.exif_transpose(img) if hasattr(img, "_getexif") and img._getexif() else img


def process_image(file_data, finding_id, config):
    storage = get_storage()
    img = Image.open(io.BytesIO(file_data))

    if hasattr(img, "_getexif") and img._getexif():
        img = ImageOps.exif_transpose(img)

    img = strip_exif(img)

    w, h = img.size
    if w * h > MAX_PIXELS:
        return None, "Image too large (decompression bomb protection)"

    max_edge = config.get("IMAGE_MAX_LONG_EDGE", 1600)
    thumb_size = config.get("IMAGE_THUMB_SIZE", 320)
    web_quality = config.get("IMAGE_WEB_QUALITY", 82)
    webp_quality = config.get("IMAGE_WEBP_QUALITY", 80)

    img_rgb = img.convert("RGB")

    web_img = img_rgb.copy()
    web_img.thumbnail((max_edge, max_edge), Image.LANCZOS)
    web_buf = io.BytesIO()
    web_img.save(web_buf, format="JPEG", quality=web_quality, optimize=True)
    web_bytes = web_buf.getvalue()

    thumb_img = img_rgb.copy()
    thumb_img.thumbnail((thumb_size, thumb_size), Image.LANCZOS)
    thumb_buf = io.BytesIO()
    thumb_img.save(thumb_buf, format="JPEG", quality=70, optimize=True)
    thumb_bytes = thumb_buf.getvalue()

    original_bytes = None
    if config.get("KEEP_ORIGINAL", False):
        orig_buf = io.BytesIO()
        img_rgb.save(orig_buf, format="JPEG", quality=90, optimize=True)
        original_bytes = orig_buf.getvalue()

    web_path = storage.save_bytes(web_bytes, finding_id, "jpg", "web")
    thumb_path = storage.save_bytes(thumb_bytes, finding_id, "jpg", "thumb")
    original_path = None
    if original_bytes:
        original_path = storage.save_bytes(original_bytes, finding_id, "jpg", "original")

    return {
        "web_path": web_path,
        "thumb_path": thumb_path,
        "original_path": original_path,
        "mime": "image/jpeg",
        "width": web_img.size[0],
        "height": web_img.size[1],
        "bytes": len(web_bytes),
    }, None


def delete_photo_files(photo, config):
    storage = get_storage()
    for path in [photo.web_path, photo.thumb_path, photo.original_path]:
        if path:
            storage.delete(path)
