#!/usr/bin/env python3
"""One-click localhost runner for NeMeSiS LOCAL SAFE.

This utility imports the official project directly. It never copies the source,
uses production storage, sends Telegram, calls Stripe, deploys or pushes.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import secrets
import socket
import ipaddress
import sqlite3
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DIR = ROOT / "data" / "local_dev"
PID_FILE = LOCAL_DIR / "nemesis_local.pid.json"
LOG_FILE = LOCAL_DIR / "nemesis_local.log"
MADRID = ZoneInfo("Europe/Madrid")


def detect_lan_ip() -> str:
    candidates: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            candidates.append(probe.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            candidates.append(str(info[4][0]))
    except OSError:
        pass
    for value in candidates:
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if address.version == 4 and address.is_private and not address.is_loopback and not address.is_link_local:
            return value
    return ""


def configure_local_environment(mode: str, port: int, db_name: str = "nemesis_local.db", lan_ip: str = "") -> None:
    mode = "INTEGRATION_TEST" if str(mode).lower() == "integration_test" else "OFFLINE_SAFE"
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["NEMESIS_LOCAL_SAFE_MODE"] = "1"
    os.environ["NEMESIS_LOCAL_MODE"] = mode
    os.environ["NEMESIS_OFFLINE_MODE"] = "0" if mode == "INTEGRATION_TEST" else "1"
    os.environ["NEMESIS_LOCAL_DB_NAME"] = Path(db_name).name
    os.environ["DB_PATH"] = str(LOCAL_DIR / Path(db_name).name)
    public_host = lan_ip or "127.0.0.1"
    os.environ["PUBLIC_BASE_URL"] = f"http://{public_host}:{port}"
    os.environ["APP_PUBLIC_URL"] = f"http://{public_host}:{port}"
    os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
    os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"] = secrets.token_urlsafe(32)
    lan_token = secrets.token_urlsafe(10)
    os.environ["NEMESIS_LOCAL_LAN_ENABLED"] = "1" if lan_ip else "0"
    os.environ["NEMESIS_LOCAL_LAN_IP"] = lan_ip
    os.environ["NEMESIS_LOCAL_LAN_TOKEN"] = lan_token
    os.environ["NEMESIS_LOCAL_LAN_EXPIRES_AT"] = (datetime.now(MADRID) + timedelta(hours=8)).replace(microsecond=0).isoformat()
    os.environ["NEMESIS_LOCAL_LAN_URL"] = f"http://{lan_ip}:{port}/m/{lan_token}" if lan_ip else ""
    os.environ["SESSION_COOKIE_SECURE"] = "0"
    os.environ["FLASK_ENV"] = "development"
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["SCHEDULER_ENABLED"] = "0"
    os.environ["ENABLE_AUTO_SYNC"] = "0"
    os.environ["DAILY_AUTOMATION_DRY_RUN"] = "1"
    os.environ["CONTINUOUS_EVOLUTION_SAFE_MODE"] = "1"
    os.environ["CONTINUOUS_EVOLUTION_STORAGE_ROOT"] = str(LOCAL_DIR / "continuous_evolution_os")
    os.environ.setdefault("NEMESIS_LOCAL_EXTERNAL_AUTHORIZED", "0")
    for name in (
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TELEGRAM_WEBHOOK_SECRET",
        "STRIPE_SECRET_KEY",
        "STRIPE_PUBLISHABLE_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_PRO_PRICE_ID",
        "STRIPE_ELITE_PRICE_ID",
        "RENDER_API_KEY",
        "RENDER_DEPLOY_HOOK_URL",
        "RENDER_SERVICE_ID",
        "AUTOMATION_SECRET",
        "SMTP_HOST",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "OPENAI_API_KEY",
    ):
        os.environ[name] = ""
    for name in (
        "ENABLE_TELEGRAM_AUTO",
        "ENABLE_TELEGRAM_AUTOMATION",
        "TELEGRAM_AUTO_SEND_ENABLED",
        "AUTO_SEND_TELEGRAM_PICKS",
        "ENABLE_AUTO_TELEGRAM_PRO",
        "ENABLE_AUTOMATED_RENDER_DEPLOY",
        "STRIPE_CUSTOMER_PORTAL_ENABLED",
        "ENABLE_LIVE_API",
        "ENABLE_ODDS_API",
        "ENABLE_API_FOOTBALL_PROVIDER",
        "ENABLE_API_FOOTBALL_LIVE_TRACKER",
    ):
        os.environ[name] = "0"
    if os.environ.get("NEMESIS_LOCAL_EXTERNAL_AUTHORIZED") != "1":
        for name in ("API_FOOTBALL_KEY", "API_SPORTS_KEY", "THE_ODDS_API_KEY", "THESPORTSDB_API_KEY", "THESPORTSDB_KEY"):
            os.environ[name] = ""


def port_available(port: int) -> bool:
    for host in ("127.0.0.1", "0.0.0.0"):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            if host == "127.0.0.1" and probe.connect_ex((host, port)) == 0:
                return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                return False
    return True


def select_port() -> int:
    for port in range(5000, 5101):
        if port_available(port):
            return port
    raise RuntimeError("No hay un puerto local libre entre 5000 y 5100.")


def _gf_mul(x: int, y: int) -> int:
    result = 0
    while y:
        if y & 1:
            result ^= x
        y >>= 1
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    return result


def _rs_generator(degree: int) -> list[int]:
    poly = [1]
    root = 1
    for _ in range(degree):
        nxt = [0] * (len(poly) + 1)
        for i, coef in enumerate(poly):
            nxt[i] ^= _gf_mul(coef, root)
            nxt[i + 1] ^= coef
        poly = nxt
        root = _gf_mul(root, 2)
    return poly


def _rs_remainder(data: list[int], degree: int) -> list[int]:
    gen = _rs_generator(degree)
    rem = [0] * degree
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        for i in range(degree):
            rem[i] ^= _gf_mul(gen[i], factor)
    return rem


def _bits_to_codewords(bits: list[int], capacity: int) -> list[int]:
    bits = bits[:]
    bits += [0] * min(4, capacity * 8 - len(bits))
    while len(bits) % 8:
        bits.append(0)
    pads = [0xEC, 0x11]
    pad_index = 0
    while len(bits) < capacity * 8:
        value = pads[pad_index % 2]
        bits.extend([(value >> shift) & 1 for shift in range(7, -1, -1)])
        pad_index += 1
    return [sum(bits[i + bit] << (7 - bit) for bit in range(8)) for i in range(0, capacity * 8, 8)]


def _reserve(matrix: list[list[int | None]], reserved: list[list[bool]], x: int, y: int, value: int) -> None:
    if 0 <= x < len(matrix) and 0 <= y < len(matrix):
        matrix[y][x] = value
        reserved[y][x] = True


def _finder(matrix, reserved, x: int, y: int) -> None:
    for dy in range(-1, 8):
        for dx in range(-1, 8):
            xx, yy = x + dx, y + dy
            if 0 <= xx < len(matrix) and 0 <= yy < len(matrix):
                value = 1 if (0 <= dx <= 6 and 0 <= dy <= 6 and (dx in {0, 6} or dy in {0, 6} or (2 <= dx <= 4 and 2 <= dy <= 4))) else 0
                _reserve(matrix, reserved, xx, yy, value)


def _alignment(matrix, reserved, cx: int, cy: int) -> None:
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            value = 1 if max(abs(dx), abs(dy)) in {0, 2} else 0
            _reserve(matrix, reserved, cx + dx, cy + dy, value)


def _format_bits(mask: int) -> int:
    data = (1 << 3) | mask  # ECC L + mask
    value = data << 10
    poly = 0x537
    for i in range(14, 9, -1):
        if (value >> i) & 1:
            value ^= poly << (i - 10)
    return ((data << 10) | value) ^ 0x5412


def build_qr_svg(text: str, scale: int = 8, border: int = 4) -> str:
    raw = text.encode('utf-8')
    if len(raw) > 48:
        raise ValueError('La URL LAN es demasiado larga para el QR local compacto.')
    size = 29  # QR version 3
    matrix: list[list[int | None]] = [[None] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]
    _finder(matrix, reserved, 0, 0)
    _finder(matrix, reserved, size - 7, 0)
    _finder(matrix, reserved, 0, size - 7)
    _alignment(matrix, reserved, 22, 22)
    for i in range(8, size - 8):
        _reserve(matrix, reserved, i, 6, 1 if i % 2 == 0 else 0)
        _reserve(matrix, reserved, 6, i, 1 if i % 2 == 0 else 0)
    _reserve(matrix, reserved, 8, size - 8, 1)
    bits = [0, 1, 0, 0]
    bits += [(len(raw) >> shift) & 1 for shift in range(7, -1, -1)]
    for byte in raw:
        bits += [(byte >> shift) & 1 for shift in range(7, -1, -1)]
    data_cw = _bits_to_codewords(bits, 55)
    codewords = data_cw + _rs_remainder(data_cw, 15)
    stream = [(byte >> shift) & 1 for byte in codewords for shift in range(7, -1, -1)]
    idx = 0
    upward = True
    x = size - 1
    while x > 0:
        if x == 6:
            x -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for y in rows:
            for xx in (x, x - 1):
                if not reserved[y][xx]:
                    bit = stream[idx] if idx < len(stream) else 0
                    idx += 1
                    mask = (xx + y) % 2 == 0
                    matrix[y][xx] = bit ^ (1 if mask else 0)
        upward = not upward
        x -= 2
    fmt = _format_bits(0)
    fmt_positions_1 = [(8,0),(8,1),(8,2),(8,3),(8,4),(8,5),(8,7),(8,8),(7,8),(5,8),(4,8),(3,8),(2,8),(1,8),(0,8)]
    fmt_positions_2 = [(size-1,8),(size-2,8),(size-3,8),(size-4,8),(size-5,8),(size-6,8),(size-7,8),(8,size-8),(8,size-7),(8,size-6),(8,size-5),(8,size-4),(8,size-3),(8,size-2),(8,size-1)]
    for i in range(15):
        bit = (fmt >> i) & 1
        for x0, y0 in (fmt_positions_1[i], fmt_positions_2[i]):
            matrix[y0][x0] = bit
    pixel = (size + border * 2) * scale
    rects = [f'<rect width="{pixel}" height="{pixel}" fill="#f8fbff"/>']
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            if value:
                rects.append(f'<rect x="{(x+border)*scale}" y="{(y+border)*scale}" width="{scale}" height="{scale}" fill="#020812"/>')
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {0} {0}" role="img" aria-label="QR NeMeSiS LOCAL m?vil">{1}</svg>'.format(pixel, ''.join(rects))


def write_lan_qr(lan_url: str) -> str:
    qr_path = LOCAL_DIR / 'nemesis_local_mobile_qr.svg'
    if lan_url:
        qr_path.write_text(build_qr_svg(lan_url), encoding='utf-8')
    else:
        qr_path.unlink(missing_ok=True)
    return str(qr_path)


def insert_row(conn: sqlite3.Connection, table: str, payload: dict[str, Any]) -> None:
    columns = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
    data = {key: value for key, value in payload.items() if key in columns}
    if not data:
        raise RuntimeError(f"El fixture local no coincide con la tabla {table}.")
    keys = list(data)
    placeholders = ",".join("?" for _ in keys)
    conn.execute(
        f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
        [data[key] for key in keys],
    )


def ensure_local_qa_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS api_football_standings_deep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id TEXT, league_name TEXT, team_id TEXT, team_name TEXT,
            rank INTEGER, played INTEGER, wins INTEGER, draws INTEGER, losses INTEGER,
            goals_for INTEGER, goals_against INTEGER, points INTEGER, form TEXT,
            description TEXT, source TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS api_football_live_events (
            id TEXT PRIMARY KEY, fixture_id TEXT, match_id TEXT, elapsed INTEGER,
            extra INTEGER, team_id TEXT, team_name TEXT, player_id TEXT,
            player_name TEXT, assist_id TEXT, assist_name TEXT,
            related_player_id TEXT, related_player_name TEXT, event_type TEXT,
            type TEXT, detail TEXT, comments TEXT, minute INTEGER,
            source TEXT, payload_json TEXT, captured_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS api_football_lineups_deep (
            id TEXT PRIMARY KEY, fixture_id TEXT, match_id TEXT, player_id TEXT,
            player_name TEXT, team_id TEXT, team_name TEXT, position TEXT,
            number TEXT, shirt_number TEXT, is_starting INTEGER,
            source TEXT, captured_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS api_football_injuries_history (
            id TEXT PRIMARY KEY, fixture_id TEXT, match_id TEXT, player_id TEXT,
            player_name TEXT, team_id TEXT, team_name TEXT, type TEXT,
            reason TEXT, source TEXT, captured_at TEXT, updated_at TEXT
        );
        """
    )


def seed_local_database(app_module) -> dict[str, Any]:
    app_module.DB_PATH = os.environ["DB_PATH"]
    app_module._SEEDED_DB_PATH = None
    app_module._SEEDING_DB_PATH = None
    app_module.APP_INITIALIZED = False
    app_module.seed_core()
    now = datetime.now(MADRID).replace(microsecond=0)
    finished = now - timedelta(days=1)
    upcoming = now + timedelta(days=1)
    second = now + timedelta(days=3)
    conn = sqlite3.connect(app_module.DB_PATH)
    try:
        ensure_local_qa_tables(conn)
        for user in (
            {
                "id": "local-client-user",
                "name": "Cliente Local",
                "username": "cliente_local",
                "email": "cliente.local@example.invalid",
                "role": "FREE",
                "membership": "FREE",
            },
            {
                "id": "local-admin-user",
                "name": "Admin Local",
                "username": "admin_local",
                "email": "admin.local@example.invalid",
                "role": "ADMIN",
                "membership": "ADMIN",
            },
        ):
            conn.execute(
                "DELETE FROM users WHERE (username=? OR email=?) AND id<>?",
                (user["username"], user["email"], user["id"]),
            )
            conn.execute(
                """INSERT INTO users(id,name,username,email,password_hash,role,membership,membership_source,membership_note,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, username=excluded.username,
                     email=excluded.email, password_hash=excluded.password_hash, role=excluded.role,
                     membership=excluded.membership, membership_source=excluded.membership_source,
                     membership_note=excluded.membership_note""",
                (
                    user["id"], user["name"], user["username"], user["email"],
                    generate_password_hash(secrets.token_urlsafe(24)), user["role"], user["membership"],
                    "LOCAL_SAFE_QA", "Cuenta exclusiva de localhost. No representa un usuario real.", now.isoformat(),
                ),
            )
        insert_row(conn, "competitions", {
            "key": "liga-local-qa", "name": "Liga Local QA", "country": "Spain",
            "scope": "League", "external_id": "local-qa-competition", "source": "SIMULATED_QA",
            "sync_status": "local_fixture", "updated_at": now.isoformat(),
        })
        teams = (
            ("club-local-qa", "Club Local QA"),
            ("rival-norte-qa", "Rival Norte QA"),
            ("rival-sur-qa", "Rival Sur QA"),
            ("rival-este-qa", "Rival Este QA"),
        )
        for key, name in teams:
            insert_row(conn, "teams", {
                "key": key, "name": name, "country": "Spain", "league": "Liga Local QA",
                "logo_url": f"/team-crest.svg?name={urllib.parse.quote_plus(name)}",
                "external_id": key, "source": "SIMULATED_QA",
                "legal_note": "Fixture local de QA. No es informacion deportiva real.",
                "sync_status": "local_fixture", "updated_at": now.isoformat(),
            })
        match_rows = (
            ("local-match-1", finished, "FT", "2", "1", "2-1", "Club Local QA", "Rival Norte QA", "club-local-qa", "rival-norte-qa"),
            ("local-match-2", upcoming, "NS", None, None, "", "Club Local QA", "Rival Sur QA", "club-local-qa", "rival-sur-qa"),
            ("local-match-3", second, "NS", None, None, "", "Rival Este QA", "Club Local QA", "rival-este-qa", "club-local-qa"),
        )
        for match_id, kickoff, status, home_score, away_score, score, home, away, home_id, away_id in match_rows:
            insert_row(conn, "matches", {
                "id": match_id, "external_id": match_id, "sport_key": "soccer",
                "match_date": kickoff.date().isoformat(), "kickoff_time": kickoff.strftime("%H:%M"),
                "match_time": kickoff.strftime("%H:%M"), "kickoff_iso": kickoff.isoformat(),
                "competition_id": "local-qa-competition", "competition_key": "liga-local-qa",
                "competition_name": "Liga Local QA", "league_name": "Liga Local QA", "country": "Spain",
                "home_team": home, "away_team": away, "home_team_id": home_id, "away_team_id": away_id,
                "home_logo": f"/team-crest.svg?name={urllib.parse.quote_plus(home)}",
                "away_logo": f"/team-crest.svg?name={urllib.parse.quote_plus(away)}",
                "status": status, "score": score, "home_score": home_score, "away_score": away_score,
                "venue": "Estadio Local QA", "season": str(now.year), "round": "Jornada local",
                "source": "SIMULATED_QA", "legal_note": "Fixture local seguro; no produccion.",
                "raw_json": json.dumps({"evidence_origin": "SIMULATED_QA", "offline": True}),
                "sync_status": "local_fixture", "updated_at": now.isoformat(),
            })
        conn.execute("DELETE FROM api_football_standings_deep WHERE league_id='local-qa-competition'")
        for rank, (team_id, team_name), points, form in (
            (1, teams[0], 25, "VVEVV"), (2, teams[1], 22, "VEVDE"),
            (3, teams[2], 17, "DEVEV"), (4, teams[3], 10, "DDVED"),
        ):
            conn.execute(
                """INSERT INTO api_football_standings_deep
                   (league_id,league_name,team_id,team_name,rank,played,wins,draws,losses,
                    goals_for,goals_against,points,form,description,source,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("local-qa-competition", "Liga Local QA", team_id, team_name, rank, 12,
                 max(1, 8-rank), rank, max(1, rank-1), 20-rank, 8+rank, points, form,
                 "Clasificacion simulada de QA", "SIMULATED_QA", now.isoformat()),
            )
        insert_row(conn, "api_football_live_events", {
            "id": "local-event-goal-1", "fixture_id": "local-match-1", "match_id": "local-match-1",
            "player_id": "local-player-101", "player_name": "Alex Local QA",
            "team_id": "club-local-qa", "team_name": "Club Local QA", "event_type": "Goal",
            "type": "Goal", "detail": "Evento simulado para comprobar la cronologia offline.",
            "elapsed": 24, "minute": 24, "source": "SIMULATED_QA",
            "captured_at": finished.isoformat(), "updated_at": now.isoformat(),
        })
        insert_row(conn, "api_football_lineups_deep", {
            "id": "local-lineup-101", "fixture_id": "local-match-1", "match_id": "local-match-1",
            "player_id": "local-player-101", "player_name": "Alex Local QA",
            "team_id": "club-local-qa", "team_name": "Club Local QA", "position": "Delantero",
            "number": "9", "shirt_number": "9", "is_starting": 1, "source": "SIMULATED_QA",
            "captured_at": finished.isoformat(), "updated_at": now.isoformat(),
        })
        insert_row(conn, "match_timeline", {
            "id": "local-timeline-goal-1", "match_id": "local-match-1", "minute": "24",
            "event_type": "Goal", "title": "Gol local de QA",
            "detail": "Cronologia simulada y marcada como QA.", "source": "SIMULATED_QA",
            "legal_note": "No es un evento deportivo real.", "created_at": finished.isoformat(),
        })
        insert_row(conn, "picks", {
            "id": "local-pick-qa-1", "match_id": "local-match-2", "match_date": upcoming.date().isoformat(),
            "sport_key": "soccer", "competition_key": "liga-local-qa", "competition_name": "Liga Local QA",
            "home_team": "Club Local QA", "away_team": "Rival Sur QA", "pick_type": "1X2",
            "selection": "Club Local QA", "odds": 1.8, "confidence": 60, "stake_units": 1,
            "status": "published", "source": "SIMULATED_QA",
            "legal_note": "Pick local de QA; no es recomendacion real.",
            "created_at": now.isoformat(), "updated_at": now.isoformat(),
        })
        conn.execute("UPDATE telegram_settings SET enabled=0, auto_daily_matches=0, auto_daily_picks=0, auto_live_alerts=0")
        conn.execute(
            "INSERT OR REPLACE INTO automation_state(key,value_json,updated_at) VALUES(?,?,?)",
            ("nemesis_local_safe", json.dumps({"mode": os.environ["NEMESIS_LOCAL_MODE"], "production": False, "external": False}), now.isoformat()),
        )
        conn.commit()
        return {"users": 2, "matches": len(match_rows), "teams": len(teams), "players": 1, "picks": 1}
    finally:
        conn.close()


def local_status(port: int, path: str = "/local-safe/status") -> tuple[int, dict[str, Any], dict[str, str]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        return response.status, payload, {key.lower(): value for key, value in response.getheaders()}
    finally:
        connection.close()


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def existing_instance() -> dict[str, Any] | None:
    if not PID_FILE.exists():
        return None
    try:
        metadata = json.loads(PID_FILE.read_text(encoding="utf-8"))
        pid = int(metadata.get("pid") or 0)
        port = int(metadata.get("port") or 0)
        if process_alive(pid) and port:
            status, payload, headers = local_status(port)
            if status == 200 and payload.get("status") == "LOCAL_SAFE_READY" and headers.get("x-nemesis-local-safe") == "1":
                return metadata
    except Exception:
        pass
    PID_FILE.unlink(missing_ok=True)
    return None


def write_pid_file(port: int, mode: str, access_url: str, lan_url: str = "", lan_ip: str = "") -> None:
    metadata = {
        "pid": os.getpid(), "port": port, "mode": mode, "project_root": str(ROOT),
        "runner": str(Path(__file__).resolve()), "access_url": access_url,
        "lan_url": lan_url, "lan_ip": lan_ip,
        "started_at_madrid": datetime.now(MADRID).replace(microsecond=0).isoformat(),
    }
    temporary = PID_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(PID_FILE)


def open_url(url: str) -> None:
    if os.getenv("NEMESIS_LOCAL_NO_BROWSER", "").strip().lower() in {"1", "true", "yes", "on"}:
        return
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass


def print_banner(mode: str, port: int, fixtures: dict[str, Any], lan_url: str = "") -> None:
    label = "OFFLINE SAFE" if mode == "OFFLINE_SAFE" else "INTEGRATION TEST"
    print("\n=============================================")
    print("          NEMESIS SHARK PRO - LOCAL")
    print("=============================================")
    print(f"MODO:        {label}")
    print("PRODUCCION:  DESCONECTADA")
    print("DB:          LOCAL")
    print("TELEGRAM:    OFF")
    print("STRIPE:      OFF")
    print("RENDER:      OFF")
    print("INTERNET:    NO NECESARIO PARA LA EXPERIENCIA LOCAL")
    print(f"URL PC:      http://127.0.0.1:{port}")
    print(f"URL MOVIL:   {lan_url or 'No disponible: no se detecto IP privada'}")
    print(f"FIXTURES QA: {fixtures.get('matches', 0)} partidos")
    print("=============================================")
    print("No cierres esta ventana mientras NeMeSiS este funcionando.\n")


def run_self_test(mode: str) -> int:
    port = select_port()
    db_name = "nemesis_local_selftest.db"
    configure_local_environment(mode, port, db_name=db_name)
    sys.path.insert(0, str(ROOT))
    import app as app_module
    from engines.stripe_payments_engine import create_checkout_session

    fixtures = seed_local_database(app_module)
    app_module.app.config.update(TESTING=True)
    token = os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"]
    client = app_module.app.test_client()
    portal = client.get(f"/local-safe?token={urllib.parse.quote(token)}", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    client_login = client.get(f"/local-safe/login/client?token={urllib.parse.quote(token)}", environ_base={"REMOTE_ADDR": "127.0.0.1"}, follow_redirects=False)
    route_status = {}
    for path in ("/app", "/match/local-match-2", "/team/club-local-qa", "/competition/liga-local-qa", "/player/local-player-101", "/shark", "/picks", "/membresias"):
        route_status[path] = client.get(path, environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code
    admin = app_module.app.test_client()
    admin_login = admin.get(f"/local-safe/login/admin?token={urllib.parse.quote(token)}", environ_base={"REMOTE_ADDR": "127.0.0.1"}, follow_redirects=False)
    founder_status = admin.get("/admin/founder-dashboard", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code
    blocked_telegram = admin.post("/api/telegram/send", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code
    blocked_stripe_route = client.post("/pagos/checkout/PRO", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code
    blocked_sync = admin.get("/api/matches/sync-now", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code
    stripe_result = create_checkout_session(app_module.DB_PATH, {"id": "local-client-user"}, "PRO")
    network_blocked = False
    try:
        urllib.request.urlopen("https://example.com", timeout=1)
    except app_module.LocalSafeExternalAccessBlocked:
        network_blocked = True
    db_isolated = Path(app_module.DB_PATH).resolve().is_relative_to(LOCAL_DIR.resolve())
    payload = {
        "ok": all(status < 500 for status in route_status.values()) and portal.status_code == 200 and client_login.status_code == 302 and admin_login.status_code == 302 and founder_status == 200 and network_blocked and db_isolated,
        "mode": os.environ["NEMESIS_LOCAL_MODE"], "fixtures": fixtures,
        "portal": portal.status_code, "client_login": client_login.status_code,
        "admin_login": admin_login.status_code, "founder": founder_status,
        "routes": route_status, "network_blocked": network_blocked,
        "telegram_blocked": blocked_telegram == 403, "stripe_route_blocked": blocked_stripe_route == 403,
        "stripe_engine_blocked": stripe_result.get("status") == "LOCAL_SAFE_BLOCKED",
        "sync_blocked": blocked_sync == 403, "db_isolated": db_isolated,
        "db_path": str(app_module.DB_PATH), "production_modified": False,
        "external_actions_executed": 0,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(str(app_module.DB_PATH) + suffix).unlink(missing_ok=True)
        except PermissionError:
            pass
    return 0 if payload["ok"] and all((payload["telegram_blocked"], payload["stripe_route_blocked"], payload["stripe_engine_blocked"], payload["sync_blocked"])) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("offline_safe", "integration_test"), default="offline_safe")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    mode = "INTEGRATION_TEST" if args.mode == "integration_test" else "OFFLINE_SAFE"
    if args.self_test:
        return run_self_test(mode)
    running = existing_instance()
    if running:
        print(f"NeMeSiS LOCAL ya esta funcionando en http://127.0.0.1:{running['port']}")
        open_url(str(running.get("access_url") or f"http://127.0.0.1:{running['port']}/local-safe"))
        return 0
    port = select_port()
    lan_ip = detect_lan_ip()
    configure_local_environment(args.mode, port, lan_ip=lan_ip)
    sys.path.insert(0, str(ROOT))
    import app as app_module

    fixtures = seed_local_database(app_module)
    bind_host = "0.0.0.0" if os.environ.get("NEMESIS_LOCAL_LAN_ENABLED") == "1" else "127.0.0.1"
    server = make_server(bind_host, port, app_module.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, name="nemesis-local-server", daemon=True)
    thread.start()
    token = os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"]
    access_url = f"http://127.0.0.1:{port}/local-safe?token={urllib.parse.quote(token)}"
    lan_url = os.environ.get("NEMESIS_LOCAL_LAN_URL", "")
    write_lan_qr(lan_url)
    for _ in range(50):
        try:
            status, payload, _headers = local_status(port)
            if status == 200 and payload.get("status") == "LOCAL_SAFE_READY":
                break
        except Exception:
            time.sleep(0.1)
    else:
        server.shutdown()
        raise RuntimeError("NeMeSiS LOCAL no supero el health check local.")
    write_pid_file(port, mode, access_url, lan_url=lan_url, lan_ip=os.environ.get("NEMESIS_LOCAL_LAN_IP", ""))
    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(f"{datetime.now(MADRID).isoformat()} START pid={os.getpid()} port={port} mode={mode}\n")
    print_banner(mode, port, fixtures, lan_url=lan_url)
    open_url(access_url)
    try:
        while thread.is_alive():
            print("[1] ABRIR COMO CLIENTE")
            print("[2] ABRIR COMO ADMIN")
            print("[3] ABRIR FOUNDER CENTER")
            print("[4] ABRIR PANEL LOCAL")
            print("[5] ABRIR EN MOVIL")
            print("[0] DETENER NEMESIS LOCAL")
            choice = input("Selecciona una opcion: ").strip()
            if choice == "1":
                open_url(f"http://127.0.0.1:{port}/local-safe/login/client?token={urllib.parse.quote(token)}")
            elif choice == "2":
                open_url(f"http://127.0.0.1:{port}/local-safe/login/admin?token={urllib.parse.quote(token)}")
            elif choice == "3":
                open_url(f"http://127.0.0.1:{port}/local-safe/login/founder?token={urllib.parse.quote(token)}")
            elif choice == "4":
                open_url(access_url)
            elif choice == "5":
                open_url(access_url + "#mobile")
            elif choice == "0":
                break
            else:
                print("Opcion no reconocida.\n")
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        server.shutdown()
        thread.join(timeout=5)
        PID_FILE.unlink(missing_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now(MADRID).isoformat()} STOP pid={os.getpid()}\n")
    print("NeMeSiS LOCAL se ha detenido correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
