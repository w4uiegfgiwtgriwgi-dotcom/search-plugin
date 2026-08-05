from __future__ import annotations
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.startswith("utm_")]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(sorted(query)), ""))

def expand_query(text: str) -> list[str]:
    raw = " ".join(text.split())
    if not raw:
        raise ValueError("query is required")
    phrases = [raw]
    replacements = {
        "高温": ["酷暑", "heat wave"],
        "废墟": ["末日废墟", "ruins"],
        "空调": ["旧空调", "air conditioner"],
        "台词": ["字幕", "对白"],
    }
    for key, values in replacements.items():
        if key in raw:
            phrases.extend(values)
    out = []
    for phrase in phrases:
        if phrase not in out:
            out.append(phrase)
    return out[:10]
