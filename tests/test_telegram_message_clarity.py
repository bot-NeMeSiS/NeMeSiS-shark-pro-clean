"""Offline message contracts from the requested Telegram presentation changes."""
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser

import pytest
from engines import telegram_message_formatter as fmt
from engines.telegram_autonomous_delivery_engine import _pick_message, _briefing_message


def fixture_match():
    now=datetime.now(timezone.utc)
    return {"id":"qa-message-only", "sport_key":"soccer_spain_la_liga",
            "home_team":"QA <Local> & Norte", "away_team":"QA Sur",
            "competition_name":"Liga QA", "kickoff_iso":(now-timedelta(minutes=20)).isoformat(),
            "status":"live", "home_score":0, "away_score":1,
            "live_updated_at":(now-timedelta(seconds=5)).isoformat(),
            "match_url":"https://example.com/match/qa-message-only"}


def test_autonomous_pick_does_not_invent_missing_financial_context():
    item={**fixture_match(), "market":"1X2", "selection":"Local"}
    title, body=_pick_message(item)
    assert title and body
    assert "1/10" not in body
    assert "0/100" not in body
    assert "Riesgo: Medio" not in body
    assert "señal positiva" not in body


def test_common_briefing_keeps_paid_selection_details_out_of_free_content():
    match=fixture_match()
    pick={**match,"market":"1X2","selection":"PRIVATE_SELECTION_QA","odds":9.87,
          "reasoning":"PRIVATE_REASON_QA", "membership_required":"ELITE"}
    _,body=_briefing_message([match],[pick])
    assert "PRIVATE_SELECTION_QA" not in body
    assert "9.87" not in body
    assert "PRIVATE_REASON_QA" not in body
    assert "Liga QA" in body


def test_live_message_shows_own_observation_and_clear_state():
    item=fixture_match()
    message=fmt.format_live_alert_message(item)
    observed=datetime.fromisoformat(item['live_updated_at']).astimezone(fmt.TZ)
    assert "EN DIRECTO" in message
    assert "Actualización de datos:" in message
    assert observed.strftime('%d/%m/%Y') in message
    assert observed.strftime('%H:%M:%S') in message
    assert "tracking" not in message.lower()


@pytest.mark.parametrize('clock', [None, 'not-a-clock', '2026-01-01T12:00:00'])
def test_missing_or_invalid_observation_never_becomes_message_creation_time(clock):
    item=fixture_match()
    item.pop('live_updated_at')
    if clock is not None:
        item['live_updated_at']=clock
    message=fmt.format_live_alert_message(item)
    assert "Actualización de datos: sin hora confirmada" in message
    assert "EN DIRECTO" not in message


def test_future_clock_is_not_presented_as_confirmed_update():
    item=fixture_match()
    future=datetime.now(timezone.utc)+timedelta(days=1)
    item['live_updated_at']=future.isoformat()
    message=fmt.format_live_alert_message(item)
    assert "Actualización de datos: hora por confirmar" in message
    assert "EN DIRECTO" not in message


def test_message_has_explicit_valid_match_link_without_privileged_fallback():
    item=fixture_match()
    message=fmt.format_prematch_message(item)
    assert item['match_url'] in message
    assert 'Ver ficha del partido' in message
    item['match_url']='https://example.com/admin/users'
    assert item['match_url'] not in fmt.format_prematch_message(item)


def test_plain_formatter_respects_utf16_budget_with_large_emoji_fields():
    message=fmt.format_pick_message({**fixture_match(), 'selection':'Local','reasoning':'🦈'*5000})
    assert len(message.encode('utf-16-le'))//2<=3900


def test_autonomous_message_escapes_names_for_actual_html_transport():
    _,body=_pick_message({**fixture_match(),'selection':'Local','market':'1X2'})
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(); self.parts=[]
        def handle_data(self,data):
            self.parts.append(data)
    text=Text(); text.feed(body)
    assert 'QA <Local> & Norte' in ''.join(text.parts)
    assert '<Local>' not in body


def test_free_preview_keeps_full_reason_odds_and_stake_private():
    item={**fixture_match(), 'selection':'Local','reasoning':'PRIVATE_REASON_QA',
          'odds':9.87,'stake_units':7.65,'confidence':0}
    message=fmt.format_membership_pick_message(item,membership='FREE')
    assert 'PRIVATE_REASON_QA' not in message
    assert '9.87' not in message
    assert '7.65' not in message


def test_date_without_kickoff_does_not_invent_a_midnight_time():
    message=fmt.format_prematch_message({'id':'qa-date-only','home_team':'QA Uno',
        'away_team':'QA Dos','competition_name':'Liga QA','match_date':'2026-11-25','status':'NS'})
    assert 'hora pendiente' in message.lower()
    assert '01:00' not in message and '00:00' not in message


def test_actual_agenda_reader_preserves_own_stored_time_and_observation():
    import sqlite3
    from engines.telegram_autonomous_delivery_engine import _matches_today, _date_key
    conn=sqlite3.connect(':memory:'); conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE matches(id TEXT,home_team TEXT,away_team TEXT,competition_name TEXT,'
                 'match_date TEXT,kickoff_time TEXT,provider_updated_at TEXT)')
    clock=datetime.now(timezone.utc).isoformat()
    conn.execute('INSERT INTO matches VALUES(?,?,?,?,?,?,?)',
                 ('qa-owned-time','Real Madrid','Barcelona','LaLiga',_date_key(),'21:00',clock))
    rows=_matches_today(conn,limit=1)
    assert len(rows)==1
    assert rows[0].get('kickoff_time')=='21:00'
    assert rows[0].get('provider_updated_at')==clock
    conn.close()
