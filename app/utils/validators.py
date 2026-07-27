import math

MAX_LAT = 90.0
MIN_LAT = -90.0
MAX_LON = 180.0
MIN_LON = -180.0
MAX_DESCRIPTION_LENGTH = 2000
MAX_LOCATION_NAME_LENGTH = 256
MAX_REPORT_REASON_LENGTH = 512
MAX_FILES_PER_FINDING = 6


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
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


def validate_location_name(text, max_len=MAX_LOCATION_NAME_LENGTH):
    if not text or not text.strip():
        return ""
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
