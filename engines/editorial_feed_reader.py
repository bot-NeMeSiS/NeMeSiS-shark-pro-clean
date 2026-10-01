"""Bounded RSS/Atom reader for explicitly reviewed HTTPS feeds.

No article crawling, redirects, proxies, cookies, enclosures or generative calls.
DNS results are checked once and the TLS socket is pinned to that public address.
The deadline is cooperative: system DNS resolution itself is not cancellable.
"""
from __future__ import annotations
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import http.client
import ipaddress
import re
import socket
import ssl
import time
import unicodedata
from urllib.parse import urlsplit, urljoin
import xml.etree.ElementTree as ET

from engines.match_news_store import NewsError, safe_url

MAX_BYTES = 262144
MAX_ENTRIES = 50
RULE = 'EXACT_TEAMS_COMPETITION_POSTMATCH_V2'


class FeedError(ValueError):
    """Only fixed reason codes are surfaced; transport messages may contain URLs."""


def normalized(value):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').lower()) if not unicodedata.combining(c))).split())


def https_feed(url, *, deadline, monotonic=time.monotonic):
    try:
        url = safe_url(url)
        p = urlsplit(url)
        def network_timeout(cap=4.):
            remaining = deadline - monotonic()
            if remaining <= 0: raise FeedError('TIME_BUDGET')
            return min(cap, remaining)
        network_timeout()
        addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise FeedError('UNSAFE_DNS')
        # No second hostname resolution: connect to the checked sockaddr.
        family, socktype, proto, _, address = addresses[0]
        sock = socket.socket(family, socktype, proto)
        conn = None
        try:
            sock.settimeout(network_timeout())
            sock.connect(address)
            sock.settimeout(network_timeout())
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=p.hostname)
            conn = http.client.HTTPConnection(p.hostname, timeout=network_timeout())
            conn.sock = sock
            sock.settimeout(network_timeout())
            conn.request('GET', p.path + ('?' + p.query if p.query else ''), headers={
                'Host': p.hostname, 'User-Agent': 'NeMeSiS-Editorial/1.0 (approved feeds only)',
                'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml',
                'Accept-Encoding': 'identity', 'Connection': 'close'})
            sock.settimeout(network_timeout())
            response = conn.getresponse()
            network_timeout()
            if 300 <= response.status < 400: raise FeedError('REDIRECT_REVIEW')
            if response.status in (401,403): raise FeedError('ACCESS_DENIED')
            if response.status == 429: raise FeedError('RATE_LIMIT')
            if response.status != 200: raise FeedError('SOURCE_UNAVAILABLE')
            if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                raise FeedError('ENCODING_UNSUPPORTED')
            declared = response.getheader('Content-Length')
            if declared is not None and (not declared.isdigit() or int(declared) > MAX_BYTES):
                raise FeedError('RESPONSE_TOO_LARGE')
            data = bytearray()
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0: raise FeedError('TIME_BUDGET')
                sock.settimeout(min(2., remaining))
                chunk = response.read1(min(16384, MAX_BYTES + 1 - len(data)))
                if not chunk: break
                data.extend(chunk)
                if len(data) > MAX_BYTES: raise FeedError('RESPONSE_TOO_LARGE')
            return bytes(data)
        finally:
            if conn: conn.close()
            sock.close()
    except FeedError:
        raise
    except (OSError, ValueError, http.client.HTTPException, UnicodeError):
        raise FeedError('NETWORK_OR_TLS') from None


def parse_feed(raw, *, feed_url, article_host, now):
    """Only small UTF-8 RSS2/Atom metadata; no XML entity expansion or article text."""
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES: raise FeedError('RESPONSE_TOO_LARGE')
    try:
        text = raw.decode('utf-8-sig')
        if '\x00' in text or re.search(r'<!\s*(DOCTYPE|ENTITY)', text, re.I):
            raise FeedError('UNSAFE_XML')
        root = ET.fromstring(text)
        all_nodes = list(root.iter())
        if len(all_nodes) > 3000: raise FeedError('FEED_TOO_COMPLEX')
        def local(node): return node.tag.rsplit('}', 1)[-1]
        if local(root) == 'rss': nodes = root.findall('./channel/item')
        elif root.tag == '{http://www.w3.org/2005/Atom}feed': nodes = root.findall('{http://www.w3.org/2005/Atom}entry')
        else: raise FeedError('UNSUPPORTED_FEED')
        items, rejected, seen = [], 0, set()
        for node in nodes[:MAX_ENTRIES]:
            values, categories = {}, []
            for child in node:
                name = local(child)
                if name == 'link' and child.get('href'):
                    if child.get('rel', 'alternate') == 'alternate': values['link'] = child.get('href')
                elif name == 'category':
                    category = (child.get('term') or ''.join(child.itertext())).strip()
                    if category: categories.append(category)
                elif name in ('title','link','pubDate','published','updated'):
                    values.setdefault(name, ''.join(child.itertext()).strip())
            try:
                link = safe_url(urljoin(feed_url, values.get('link','')))
                if not values.get('link') or urlsplit(link).hostname != article_host: raise ValueError()
                title = values.get('title','')
                if not 6 <= len(title) <= 400 or re.search(r'[<>\x00-\x1f]', title): raise ValueError()
                date = values.get('pubDate') or values.get('published') or values.get('updated') or ''
                try: dt = datetime.fromisoformat(date.replace('Z','+00:00'))
                except ValueError: dt = parsedate_to_datetime(date)
                if dt.tzinfo is None or not now - 7*86400 <= dt.timestamp() <= now: raise ValueError()
                # One URL appearing twice with conflicting metadata is ambiguous, not first-wins.
                if link in seen:
                    items = [i for i in items if i['url'] != link]
                    rejected += 1
                    continue
                seen.add(link)
                items.append({'url':link, 'title':title, 'published_at':dt.astimezone(timezone.utc).isoformat(),
                              'published_ts':dt.timestamp(), 'category':categories[0] if categories else '',
                              'categories':categories})
            except (NewsError, ValueError, TypeError, OverflowError): rejected += 1
        return items, rejected
    except FeedError:
        raise
    except (UnicodeError, ET.ParseError, ValueError): raise FeedError('MALFORMED_FEED') from None


def match_article(item, matches, source, now):
    """Both exact full canonical names + reviewed competition + narrow date window.

Never fuzzy-matches aliases, assumes a final, or treats a match as identified by
one team. Even this rule is editorial association, not proof of article claims.
"""
    from engines.postmatch_store import is_final
    from engines.v935_launch_trust_engine import match_kickoff_madrid
    title, hits = ' ' + normalized(item['title']) + ' ', []
    competition = normalized(source['competition'])
    categories = item.get('categories') or ([item['category']] if item.get('category') else [])
    # A reviewed feed scope cannot override an explicit conflicting article tag.
    # Unknown tags require review instead of inventing competition aliases.
    if any(normalized(category) != competition for category in categories):
        return None, 'CATEGORY_REVIEW'
    for match in matches:
        if not is_final(match, now): continue
        if competition not in {normalized(match.get('competition_name')), normalized(match.get('league_name'))}: continue
        home, away = normalized(match.get('home_team')), normalized(match.get('away_team'))
        if len(home) < 4 or len(away) < 4 or home == away: continue
        if ' '+home+' ' not in title or ' '+away+' ' not in title: continue
        if any(re.search(r'\b'+re.escape(team)+r'\s+(?:b|c|femenin[oa]|femeni|women|u[0-9]{2}|sub ?[0-9]{2})\b', title) for team in (home,away)): continue
        kickoff = match_kickoff_madrid(match)
        if not kickoff or not 0 <= item['published_ts'] - kickoff.timestamp() <= 48*3600: continue
        hits.append(match)
    return (hits[0], 'MATCHED') if len(hits) == 1 else (None, 'AMBIGUOUS' if hits else 'UNMATCHED')
