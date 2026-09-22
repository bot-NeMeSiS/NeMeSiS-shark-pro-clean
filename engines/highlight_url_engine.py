"""Video URL validation only. Never requests or downloads a resource."""
from __future__ import annotations

import hashlib
import ipaddress
import re
from urllib.parse import parse_qs, urlsplit


def public_https_url(value) -> str:
    raw = str(value or '').strip()
    if not raw or len(raw) > 2048 or '\\' in raw or re.search(r'[\x00-\x20\x7f]', raw):
        return ''
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or '').lower()
        if parsed.scheme != 'https' or not host or parsed.username or parsed.password:
            return ''
        if parsed.port not in (None, 443) or '.' not in host or host.endswith(('.local', '.localhost')):
            return ''
        if not re.fullmatch(r'[a-z0-9.-]+', host) or host.startswith('.') or host.endswith('.') or '..' in host or not re.search(r'[a-z]', host.rsplit('.', 1)[-1]):
            return ''
        try:
            if not ipaddress.ip_address(host).is_global:
                return ''
        except ValueError:
            pass
        return raw
    except (ValueError, TypeError):
        return ''


def video_identity(value) -> tuple[str, str] | None:
    raw = public_https_url(value)
    if not raw:
        return None
    parsed = urlsplit(raw)
    host = parsed.hostname.lower()
    path = parsed.path.strip('/').split('/')
    identifier = ''
    if host == 'youtu.be' and len(path) == 1:
        identifier = path[0]
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com'}:
        if parsed.path == '/watch':
            values = parse_qs(parsed.query).get('v', [])
            identifier = values[0] if len(values) == 1 else ''
        elif len(path) == 2 and path[0] in {'embed', 'shorts'}:
            identifier = path[1]
    if identifier and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', identifier):
        return 'youtube', identifier
    if host in {'vimeo.com', 'www.vimeo.com', 'player.vimeo.com'}:
        identifier = path[-1] if path else ''
        if identifier.isascii() and identifier.isdigit() and len(identifier) <= 20:
            if len(path) == 1 or (len(path) == 2 and path[0] == 'video'):
                return 'vimeo', identifier
    return None


def safe_embed_url(original, proposed='') -> str:
    identity = video_identity(original)
    if not identity or (proposed and video_identity(proposed) != identity):
        return ''
    provider, identifier = identity
    if provider == 'youtube':
        return 'https://www.youtube-nocookie.com/embed/' + identifier
    return 'https://player.vimeo.com/video/' + identifier


def review_fingerprint(row) -> str:
    """Bind a human decision to the exact current URL and match association."""
    fields = ('id', 'sportsdb_event_id', 'match_id', 'video_url', 'embed_url', 'thumbnail_url',
              'home_team', 'away_team', 'event_date', 'league_id', 'rights_status',
              'commercial_use_status', 'rights_verified_at', 'embed_policy', 'allowed_channels_json',
              'attribution', 'attribution_required', 'official_source_verified',
              'geo_restriction_status', 'thumbnail_rights_status',
              'thumbnail_commercial_use_status', 'thumbnail_attribution',
              'rights_note', 'status', 'client_status', 'source', 'provider',
              'updated_at', 'review_revision')
    import json
    value = {key: str(row.get(key) or '') for key in fields}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
