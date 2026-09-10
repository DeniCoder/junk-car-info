import math
import re

MAX_LAT = 90.0
MIN_LAT = -90.0
MAX_LON = 180.0
MIN_LON = -180.0
MAX_DESCRIPTION_LENGTH = 2000
MAX_LOCATION_NAME_LENGTH = 256
MAX_REPORT_REASON_LENGTH = 512
MAX_FILES_PER_FINDING = 6


def sanitize_input(text, max_len=1000):
    """Sanitize user input to prevent XSS and injection attacks."""
    if not text:
        return ""
    text = str(text).strip()
    # Remove potentially dangerous HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    # Remove script-like patterns
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    if len(text) > max_len:
        text = text[:max_len]
    return text


def validate_lat_lon(lat, lon):
    errors = []
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None, None, ["coordinates must be valid numbers"]
    if not (MIN_LAT <= lat <= MAX_LAT):
        errors.append(f"latitude must be between {MIN_LAT} and {MAX_LAT}")
    if not (MIN_LON <= lon <= MAX_LON):
        errors.append(f"longitude must be between {MIN_LON} and {MAX_LON}")
    return lat, lon, errors


def validate_description(text, max_len=MAX_DESCRIPTION_LENGTH):
    if not text or not text.strip():
        return ""
    text = sanitize_input(text, max_len)
    if not text.strip():
        return ""
    return text


def validate_location_name(text, max_len=MAX_LOCATION_NAME_LENGTH):
    if not text or not text.strip():
        return ""
    text = sanitize_input(text, max_len)
    if not text.strip():
        return ""
    return text


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
