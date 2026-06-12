import hashlib
import json
import sqlite3
import re

from engines.telegram_sport_filter_engine import is_telegram_football_item, telegram_sport_filter_reason
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')


def _now():
    return datetime.now(TZ).isoformat(timespec='seconds')


def _date_key():
    return datetime.now(TZ).date().isoformat()


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn, sql, args=()):
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def _one(conn, sql, args=()):
    row = conn.execute(sql, args).fetchone()
    return dict(row) if row else None


def _table_exists(conn, table):
    return bool(_one(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)))


def _cols(conn, table):
    if not _table_exists(conn, table):
        return set()
    return {r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_telegram_autonomous_schema(db_path):
    with _connect(db_path) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS telegram_auto_campaigns(
            id TEXT PRIMARY KEY,
            campaign_type TEXT,
            membership_target TEXT,
            title TEXT,
            body TEXT,
            source_key TEXT,
            priority INTEGER DEFAULT 50,
            status TEXT DEFAULT 'queued',
            queued_count INTEGER DEFAULT 0,
            sent_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0,
            payload_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS telegram_auto_rules(
            id TEXT PRIMARY KEY,
            rule_key TEXT UNIQUE,
            enabled INTEGER DEFAULT 1,
            membership_target TEXT DEFAULT 'FREE',
            min_confidence INTEGER DEFAULT 65,
            min_priority INTEGER DEFAULT 50,
            cooldown_minutes INTEGER DEFAULT 240,
            payload_json TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS telegram_delivery_memory(
            id TEXT PRIMARY KEY,
            dedupe_key TEXT UNIQUE,
            chat_id TEXT,
            user_id TEXT,
            message_type TEXT,
            membership TEXT,
            status TEXT,
            created_at TEXT
        )''')
        now = _now()
        defaults = [
            ('daily_briefing', 'FREE', 55, 40, 720),
            ('top_pick', 'PRO', 68, 70, 360),
            ('elite_value_alert', 'ELITE', 76, 85, 240),
            ('live_risk_alert', 'PRO', 65, 80, 120),
        ]
        for key, membership, conf, priority, cooldown in defaults:
            conn.execute('''INSERT OR IGNORE INTO telegram_auto_rules
                (id, rule_key, enabled, membership_target, min_confidence, min_priority, cooldown_minutes, payload_json, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                (hashlib.md5(key.encode()).hexdigest()[:18], key, 1, membership, conf, priority, cooldown, '{}', now))
        conn.commit()
    return {'ok': True, 'schema': 'telegram_autonomous_delivery'}


def _membership_rank(value):
    return {'FREE': 0, 'PRO': 1, 'ELITE': 2, 'ADMIN': 3}.get(str(value or 'FREE').upper(), 0)


def _allowed(user_membership, target):
    return _membership_rank(user_membership) >= _membership_rank(target)


def _clean_text(value, limit=180):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"\b(None|null|undefined|nan)\b", "", text, flags=re.I).strip()
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def _valid_odds(value):
    try:
        odds = float(str(value).replace(",", "."))
    except Exception:
        return ""
    if odds <= 1:
        return ""
    return f"{odds:.2f}".rstrip("0").rstrip(".")


def _selection_label(pick):
    raw = str(pick.get('selection') or pick.get('pick_type') or 'Pick SHARK').strip()
    home = pick.get('home_team') or 'Local'
    away = pick.get('away_team') or 'Visitante'
    low = raw.lower()
    if re.search(r"(esperar|pendiente|sin cuota|value en c[aá]lculo|undefined|null|none)", raw, flags=re.I):
        return ''
    if low in {'home', 'local', '1'}:
        return f"Gana {home}"
    if low in {'away', 'visitante', '2'}:
        return f"Gana {away}"
    if low in {'draw', 'empate', 'x'}:
        return 'Empate'
    over = re.search(r"over\s*([0-9]+(?:[\.,][0-9]+)?)", raw, flags=re.I)
    if over:
        return f"Más de {over.group(1).replace(',', '.')} goles"
    under = re.search(r"under\s*([0-9]+(?:[\.,][0-9]+)?)", raw, flags=re.I)
    if under:
        return f"Menos de {under.group(1).replace(',', '.')} goles"
    return _clean_text(raw, 90)


def _queue_insert(conn, *, chat_id, user_id, membership, message_type, title, body, priority, source_key, campaign_id):
    now = _now()
    dedupe = f"auto:{_date_key()}:{message_type}:{source_key}:{chat_id or user_id or 'global'}"
    memory_id = hashlib.md5(('memory:' + dedupe).encode()).hexdigest()[:22]
    exists = _one(conn, 'SELECT id FROM telegram_delivery_memory WHERE dedupe_key=?', (dedupe,))
    if exists:
        return 'skipped'
    qcols = _cols(conn, 'telegram_queue')
    if not qcols:
        return 'skipped'
    qid = hashlib.md5(('queue:' + dedupe).encode()).hexdigest()[:22]
    signature = hashlib.md5(('sig:' + dedupe).encode()).hexdigest()
    payload = json.dumps({'campaign_id': campaign_id, 'source_key': source_key, 'membership': membership}, ensure_ascii=False)
    fields = {
        'id': qid,
        'signature': signature,
        'alert_type': message_type,
        'target_key': source_key,
        'chat_id': chat_id or '',
        'user_id': user_id or '',
        'message_type': message_type,
        'title': title,
        'body': body,
        'priority': int(priority or 50),
        'payload_json': payload,
        'status': 'PENDING',
        'attempts': 0,
        'max_attempts': 3,
        'dedupe_key': dedupe,
        'scheduled_at': now,
        'created_at': now,
        'updated_at': now,
    }
    insert_cols = [k for k in fields if k in qcols]
    placeholders = ','.join(['?'] * len(insert_cols))
    sql = f"INSERT OR IGNORE INTO telegram_queue ({','.join(insert_cols)}) VALUES ({placeholders})"
    conn.execute(sql, tuple(fields[k] for k in insert_cols))
    conn.execute('''INSERT OR IGNORE INTO telegram_delivery_memory
        (id,dedupe_key,chat_id,user_id,message_type,membership,status,created_at)
        VALUES (?,?,?,?,?,?,?,?)''', (memory_id, dedupe, chat_id or '', user_id or '', message_type, membership, 'queued', now))
    return 'queued'


def _subscribers(conn):
    if not _table_exists(conn, 'telegram_subscribers'):
        return []
    cols = _cols(conn, 'telegram_subscribers')
    wanted = ['id','user_id','chat_id','membership','is_active','last_seen']
    select = ','.join([c for c in wanted if c in cols])
    if not select:
        return []
    where = 'WHERE COALESCE(is_active,1)=1' if 'is_active' in cols else ''
    return _rows(conn, f'SELECT {select} FROM telegram_subscribers {where} LIMIT 500')


def _top_picks(conn, limit=8):
    if not _table_exists(conn, 'picks'):
        return []
    cols = _cols(conn, 'picks')
    select = ','.join([c for c in ['id','home_team','away_team','competition_name','selection','pick_type','market','odds','confidence','risk_level','membership_required','status','reasoning','match_date'] if c in cols])
    if not select:
        return []
    order = 'confidence DESC' if 'confidence' in cols else 'created_at DESC'
    where_parts = []
    if 'status' in cols:
        where_parts.append("LOWER(COALESCE(status,'')) IN ('published','pending','active','')")
    where = ('WHERE ' + ' AND '.join(where_parts)) if where_parts else ''
    data = _rows(conn, f'SELECT {select} FROM picks {where} ORDER BY {order} LIMIT ?', (limit * 3,))
    return [item for item in data if is_telegram_football_item(item)][:limit]


def _matches_today(conn, limit=6):
    if not _table_exists(conn, 'matches'):
        return []
    cols = _cols(conn, 'matches')
    select = ','.join([c for c in ['id','home_team','away_team','competition_name','match_date','status','score'] if c in cols])
    if not select:
        return []
    today = _date_key()
    date_col = 'match_date' if 'match_date' in cols else None
    if date_col:
        data = _rows(conn, f'SELECT {select} FROM matches WHERE {date_col} LIKE ? ORDER BY {date_col} ASC LIMIT ?', (today + '%', limit * 3))
        return [item for item in data if is_telegram_football_item(item)][:limit]
    data = _rows(conn, f'SELECT {select} FROM matches LIMIT ?', (limit * 3,))
    return [item for item in data if is_telegram_football_item(item)][:limit]


def _pick_message(pick, elite=False):
    if not is_telegram_football_item(pick or {}):
        return '', ''
    teams = f"{pick.get('home_team') or 'Local'} vs {pick.get('away_team') or 'Visitante'}"
    selection = _selection_label(pick) or 'Pick SHARK'
    odds = _valid_odds(pick.get('odds')) or 'cuota real pendiente'
    confidence = int(float(pick.get('confidence') or 0))
    risk = _clean_text(pick.get('risk_level') or 'Medio', 40)
    reason = _clean_text(pick.get('reasoning') or 'SHARK detecta señal positiva con los datos disponibles.', 180)
    title = ('🦈 ELITE SHARK SIGNAL' if elite else '🦈 PICK SHARK PREMIUM')
    body = (
        f"{title}\n\n"
        f"{teams}\n\n"
        f"✅ Pick: {selection}\n"
        f"💰 Cuota: {odds}\n"
        f"📌 Stake: 1/10\n"
        f"📊 Confianza SHARK: {confidence}/100\n"
        f"⚠️ Riesgo: {risk}\n\n"
        f"Motivo: {reason}\n\n"
        f"Precaución: revisar contexto y no subir stake si la cuota baja.\n"
        f"Juego responsable: ningún pick garantiza resultado."
    )
    return title, body


def _briefing_message(matches, picks):
    lines = ['🦈 RESUMEN SHARK DEL DÍA', '']
    lines.append(f"⚽ Partidos monitorizados: {len(matches or [])}")
    valid_picks = [p for p in (picks or []) if is_telegram_football_item(p) and _valid_odds(p.get('odds')) and _selection_label(p)]
    lines.append(f"✅ Picks premium listos: {len(valid_picks)}")
    lines.append('')
    if matches:
        lines.append('Partidos destacados:')
        for m in matches[:5]:
            lines.append(f"• {m.get('home_team','Local')} vs {m.get('away_team','Visitante')} — {m.get('competition_name','Competición')}")
    else:
        lines.append('Hoy no hay partidos destacados cargados todavía. SHARK seguirá revisando datos.')
    if valid_picks:
        lines.append('')
        lines.append('Top señales con cuota real:')
        for p in valid_picks[:3]:
            lines.append(f"• {p.get('home_team','Local')} vs {p.get('away_team','Visitante')} → {_selection_label(p)} @{_valid_odds(p.get('odds'))}")
    else:
        lines.append('')
        lines.append('No hay picks premium cerrados ahora mismo. Mejor esperar que enviar señales débiles.')
    lines.append('')
    lines.append('Apuesta siempre con responsabilidad. SHARK prioriza calidad antes que cantidad.')
    return '🦈 Resumen SHARK del día', '\n'.join(lines)


def run_telegram_autonomous_delivery(db_path, limit=30, force=False):
    ensure_telegram_autonomous_schema(db_path)
    with _connect(db_path) as conn:
        now = _now()
        subscribers = _subscribers(conn)
        picks = _top_picks(conn, limit=10)
        matches = _matches_today(conn, limit=8)
        campaigns = []
        queued = skipped = 0

        if subscribers:
            cid = hashlib.md5(f"briefing:{_date_key()}".encode()).hexdigest()[:22]
            title, body = _briefing_message(matches, picks)
            q = s = 0
            for sub in subscribers[:limit]:
                status = _queue_insert(conn, chat_id=sub.get('chat_id'), user_id=sub.get('user_id'), membership=sub.get('membership') or 'FREE', message_type='daily_briefing', title=title, body=body, priority=55, source_key=_date_key(), campaign_id=cid)
                if status == 'queued': q += 1
                else: s += 1
            conn.execute('''INSERT OR REPLACE INTO telegram_auto_campaigns
                (id,campaign_type,membership_target,title,body,source_key,priority,status,queued_count,sent_count,skipped_count,payload_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (cid,'daily_briefing','FREE',title,body,_date_key(),55,'queued',q,0,s,json.dumps({'matches':len(matches),'picks':len(picks)}, ensure_ascii=False),now,now))
            queued += q; skipped += s; campaigns.append({'id': cid, 'type': 'daily_briefing', 'queued': q, 'skipped': s})

        for pick in picks[:5]:
            conf = int(float(pick.get('confidence') or 0))
            target = str(pick.get('membership_required') or ('ELITE' if conf >= 76 else 'PRO')).upper()
            if conf < 68 and not force:
                continue
            elite = target == 'ELITE' or conf >= 76
            cid = hashlib.md5(f"pick:{pick.get('id')}:{_date_key()}".encode()).hexdigest()[:22]
            title, body = _pick_message(pick, elite=elite)
            if not body:
                skipped += 1
                campaigns.append({'type': 'pick_skipped', 'reason': telegram_sport_filter_reason(pick) or 'no_body', 'pick': pick.get('id')})
                continue
            q = s = 0
            for sub in subscribers[:limit]:
                member = str(sub.get('membership') or 'FREE').upper()
                if not _allowed(member, target):
                    s += 1
                    continue
                status = _queue_insert(conn, chat_id=sub.get('chat_id'), user_id=sub.get('user_id'), membership=member, message_type='elite_value_alert' if elite else 'top_pick', title=title, body=body, priority=90 if elite else 75, source_key=str(pick.get('id') or ''), campaign_id=cid)
                if status == 'queued': q += 1
                else: s += 1
            conn.execute('''INSERT OR REPLACE INTO telegram_auto_campaigns
                (id,campaign_type,membership_target,title,body,source_key,priority,status,queued_count,sent_count,skipped_count,payload_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (cid,'elite_value_alert' if elite else 'top_pick',target,title,body,str(pick.get('id') or ''),90 if elite else 75,'queued',q,0,s,json.dumps(pick, ensure_ascii=False),now,now))
            queued += q; skipped += s; campaigns.append({'id': cid, 'type': 'elite_value_alert' if elite else 'top_pick', 'queued': q, 'skipped': s, 'pick': pick.get('id')})

        conn.commit()
    return {'ok': True, 'queued': queued, 'skipped': skipped, 'campaigns': campaigns, 'subscribers': len(subscribers), 'picks_checked': len(picks)}


def telegram_autonomous_summary(db_path):
    ensure_telegram_autonomous_schema(db_path)
    with _connect(db_path) as conn:
        campaigns = _one(conn, 'SELECT COUNT(*) AS total FROM telegram_auto_campaigns') or {'total': 0}
        memory = _one(conn, 'SELECT COUNT(*) AS total FROM telegram_delivery_memory') or {'total': 0}
        queued = {'total': 0}
        pending = {'total': 0}
        if _table_exists(conn, 'telegram_queue'):
            queued = _one(conn, "SELECT COUNT(*) AS total FROM telegram_queue") or {'total': 0}
            pending = _one(conn, "SELECT COUNT(*) AS total FROM telegram_queue WHERE LOWER(COALESCE(status,'')) IN ('pending','queued')") or {'total': 0}
        subs = len(_subscribers(conn))
        latest = _rows(conn, 'SELECT * FROM telegram_auto_campaigns ORDER BY created_at DESC LIMIT 8')
        rules = _rows(conn, 'SELECT * FROM telegram_auto_rules ORDER BY rule_key ASC')
    score = min(100, 35 + min(25, subs * 5) + min(20, int(campaigns.get('total') or 0) * 4) + min(20, int(memory.get('total') or 0)))
    return {
        'ok': True,
        'score': score,
        'status': 'Automático' if score >= 70 else 'Preparado',
        'subscribers': subs,
        'campaigns_total': int(campaigns.get('total') or 0),
        'delivery_memory_total': int(memory.get('total') or 0),
        'queue_total': int(queued.get('total') or 0),
        'queue_pending': int(pending.get('total') or 0),
        'rules': rules,
        'latest_campaigns': latest,
        'next_actions': [
            'Activar TELEGRAM_AUTO_ENABLED cuando quieras envío real automático.',
            'Revisar cola antes de procesar mensajes masivos.',
            'Conectar este motor al cron de Render para resumen diario y top picks.',
        ],
    }
