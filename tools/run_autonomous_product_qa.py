#!/usr/bin/env python3
"""Real-browser product QA workforce for NeMeSiS.

The runner uses an isolated QA database by default, blocks external providers,
performs exact clicks and captures the rendered application. It never sends
Telegram, touches Stripe, changes production users or runs inside a web request.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import threading
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.autonomous_product_qa_engine import record_product_qa_run  # noqa: E402
from tools.run_action_platform_browser_qa import seed_action_data  # noqa: E402
from tools.run_competition_center_browser_qa import (  # noqa: E402
    BLOCKED_PROVIDER_HOSTS,
    PROFILES,
    madrid_now,
    seed_database,
)


MADRID = ZoneInfo("Europe/Madrid")
CLIENT_TOPBAR = [
    ("Inicio", "/app"),
    ("Partidos", "/calendar"),
    ("Directo", "/live"),
    ("Picks", "/picks"),
    ("Histórico", "/track-record"),
    ("SHARK", "/shark"),
    ("Telegram", "/telegram"),
    ("Cuenta", "/profile"),
]
CLIENT_BOTTOM = [
    ("Inicio", "/app"),
    ("Partidos", "/calendar"),
    ("Directo", "/live"),
    ("Picks", "/picks"),
    ("Cuenta", "/profile"),
]
SCREENS = [
    ("landing", "/landing", "public"),
    ("public_home", "/", "public"),
    ("home", "/app", "client"),
    ("partidos", "/calendar", "client"),
    ("directo", "/live", "client"),
    ("match", "/match/m-1", "client"),
    ("team", "/team/Club%20Norte", "client"),
    ("competition", "/competition/140", "client"),
    ("player", "/player/101", "client"),
    ("picks", "/picks", "client"),
    ("shark", "/shark", "client"),
    ("track_record", "/track-record", "client"),
    ("membership", "/memberships", "client"),
    ("telegram", "/telegram", "client"),
    ("profile", "/profile", "client"),
    ("admin", "/admin/dashboard", "admin"),
    ("admin_telegram", "/admin/telegram/command-center", "admin"),
    ("admin_payments", "/admin/payments", "admin"),
    ("admin_automation", "/admin/automation-center", "admin"),
    ("admin_data_marketplace", "/admin/data-marketplace", "admin"),
    ("admin_real_launch", "/admin/real-launch", "admin"),
    ("admin_picks", "/admin/picks", "admin"),
    ("founder", "/admin/founder-dashboard", "admin"),
    ("growth", "/admin/founder-dashboard#growth-revenue", "admin"),
    ("operations", "/admin/operations-center", "admin"),
]
CRITICAL_SCREEN_KEYS = {"landing", "public_home", "home", "partidos", "directo", "match", "profile", "founder"}
TECHNICAL_COPY_RE = re.compile(
    r"(?:provider|cache\s+(?:hit|miss)|sync\s+interval|next\s+refresh|"
    r"pr[oó]xima\s+revisi[oó]n\s+en\s+\d+\s*s|\bengine\b|raw\s+enum|"
    r"traceback|sqlite3\.|operationalerror|\bnone\b|\bnull\b|\bundefined\b)",
    re.I,
)
MOJIBAKE_RE = re.compile(r"(?:\ufffd|Ã.|Â.|actualizaci\?n|informaci\?n|revisi\?n|navegaci\?n)", re.I)
LAYOUT_GATE_PROFILES = {
    "desktop_1440x900": {"width": 1440, "height": 900, "is_mobile": False},
    "desktop_1366x768": {"width": 1366, "height": 768, "is_mobile": False},
    "tablet_1024x768": {"width": 1024, "height": 768, "is_mobile": False},
    "tablet_834x1194": {"width": 834, "height": 1194, "is_mobile": False},
    "tablet_768x1024": {"width": 768, "height": 1024, "is_mobile": False},
    "mobile_430x932": {"width": 430, "height": 932, "is_mobile": True},
    "mobile_390x844": {"width": 390, "height": 844, "is_mobile": True},
    "mobile_375x812": {"width": 375, "height": 812, "is_mobile": True},
    "mobile_360x800": {"width": 360, "height": 800, "is_mobile": True},
}
EXTENDED_LAYOUT_SCREEN_KEYS = {
    "home", "partidos", "directo", "match", "team", "competition", "player",
    "picks", "shark", "track_record", "membership", "telegram", "profile",
    "admin", "founder", "growth",
}


def _session_cookie(app_module, role: str) -> str:
    serializer = app_module.app.session_interface.get_signing_serializer(app_module.app)
    if role == "admin":
        payload = {
            "user_id": "qa-admin-autonomous-product",
            "user_name": "Admin QA",
            "username": "admin_qa",
            "user_email": "admin-qa@example.invalid",
            "user_role": "ADMIN",
            "user_membership": "ADMIN",
            "membership": "ADMIN",
        }
    else:
        payload = {
            "user_id": "qa-action-platform",
            "user_name": "Cliente QA",
            "username": "cliente_qa",
            "user_email": "qa-action@example.invalid",
            "user_role": "PRO",
            "user_membership": "PRO",
            "membership": "PRO",
        }
    return serializer.dumps(payload)


def _seed_extra(db_path: Path, qa_password: str) -> None:
    from werkzeug.security import generate_password_hash
    from engines.api_football_live_tracker_engine import ensure_live_tracker_schema
    from engines.sportsdb_highlights_engine import ensure_sportsdb_highlights_schema

    seed_action_data(db_path)
    ensure_live_tracker_schema(str(db_path))
    connection = sqlite3.connect(db_path)
    try:
        now = madrid_now()
        password_hash = generate_password_hash(qa_password)
        connection.execute(
            """INSERT OR REPLACE INTO users(id,name,username,email,password_hash,role,membership,created_at,last_login)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            ("qa-admin-autonomous-product", "Admin QA", "admin_qa", "admin-qa@example.invalid", password_hash, "ADMIN", "ADMIN", now, now),
        )
        connection.execute(
            """INSERT OR REPLACE INTO users(id,name,username,email,password_hash,role,membership,created_at,last_login)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            ("qa-client-autonomous-product", "Cliente QA", "cliente_qa", "client-qa@example.invalid", password_hash, "FREE", "FREE", now, now),
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS player_registry(
                player_id TEXT PRIMARY KEY, player_name TEXT, team_id TEXT,
                team_name TEXT, competition_id TEXT, competition_name TEXT,
                source TEXT, updated_at TEXT
            )"""
        )
        connection.execute(
            """INSERT OR REPLACE INTO player_registry(player_id,player_name,team_id,team_name,competition_id,competition_name,source,updated_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            ("101", "Jugador QA", "club-norte", "Club Norte", "140", "Liga Real", "browser_qa_temp_db", now),
        )
        today = datetime.now(MADRID).date().isoformat()
        tomorrow = (datetime.now(MADRID).date() + timedelta(days=1)).isoformat()
        connection.execute(
            "UPDATE matches SET match_date=?, kickoff_iso=?, updated_at=? WHERE id='m-1'",
            (today, today + "T20:30:00+02:00", now),
        )
        connection.execute(
            "UPDATE matches SET match_date=?, kickoff_iso=?, updated_at=? WHERE id='m-2'",
            (tomorrow, tomorrow + "T20:30:00+02:00", now),
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS api_football_lineups_deep(
                id TEXT PRIMARY KEY, fixture_id TEXT, team_id TEXT, team_name TEXT,
                player_id TEXT, player_name TEXT, position TEXT, number TEXT,
                is_starting INTEGER, captured_at TEXT
            )"""
        )
        connection.execute(
            """INSERT OR REPLACE INTO api_football_lineups_deep(
                id,fixture_id,team_id,team_name,player_id,player_name,position,number,is_starting,captured_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            ("pqa-lineup-101", "m-1", "club-norte", "Club Norte", "101", "Jugador QA", "MED", "8", 1, now),
        )
        connection.execute(
            """INSERT OR REPLACE INTO api_football_live_snapshots(
                fixture_id,match_id,league_id,league_name,country,season,round_name,
                kickoff_iso,match_date,status_short,status_long,elapsed,
                home_team_id,away_team_id,home_team,away_team,home_score,away_score,
                venue,payload_json,first_seen_at,last_synced_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "m-1", "m-1", "140", "Liga Real", "Spain", "2026", "Jornada 12",
                today + "T20:30:00+02:00", today, "FT", "Match Finished", 90,
                "club-norte", "club-sur", "Club Norte", "Club Sur", 2, 0,
                "Estadio Temporal QA", '{"evidence_origin":"SIMULATED_QA"}', now, now,
            ),
        )
        connection.execute(
            """INSERT OR REPLACE INTO api_football_live_events(
                id,fixture_id,elapsed,extra,team_id,team_name,player_id,player_name,
                event_type,detail,payload_json,captured_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("pqa-event-1", "m-1", 24, 0, "club-norte", "Club Norte", "101", "Jugador QA", "Goal", "Normal Goal", '{"evidence_origin":"SIMULATED_QA"}', now),
        )
        for stat_id, team_id, team_name, value in (
            ("pqa-stat-1", "club-norte", "Club Norte", "55%"),
            ("pqa-stat-2", "club-sur", "Club Sur", "45%"),
        ):
            connection.execute(
                """INSERT OR REPLACE INTO api_football_live_stats(
                    id,fixture_id,team_id,team_name,stat_name,stat_value,numeric_value,payload_json,captured_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (stat_id, "m-1", team_id, team_name, "Ball Possession", value, float(value.rstrip("%")), '{"evidence_origin":"SIMULATED_QA"}', now),
            )
        connection.commit()
    finally:
        connection.close()
    ensure_sportsdb_highlights_schema(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """INSERT OR REPLACE INTO sportsdb_match_highlights(
                id,match_id,title,video_url,embed_url,source,provider,status,client_status,
                rights_status,commercial_use_status,attribution,attribution_required,
                rights_verified_at,official_source_verified,geo_restriction_status,
                rights_note,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "pqa-video-1", "m-1", "Resumen autorizado QA",
                "https://www.youtube.com/watch?v=rights-qa", "https://www.youtube-nocookie.com/embed/rights-qa",
                "SIMULATED_QA", "LOCAL_QA", "AUTHORIZED", "AUTHORIZED", "LICENSED", "ALLOWED",
                "Canal oficial QA", 0, now, 1, "RESTRICTED",
                "Fixture aislado SIMULATED_QA; no es evidencia de producción.", now, now,
            ),
        )
        connection.commit()


def _route_guard(route, request) -> None:
    host = urlparse(request.url).hostname or ""
    if host in {"127.0.0.1", "localhost"}:
        route.continue_()
    else:
        route.abort()


def _set_role_cookie(context, app_module, role: str) -> None:
    context.add_cookies([
        {
            "name": app_module.app.config.get("SESSION_COOKIE_NAME", "session"),
            "value": _session_cookie(app_module, role),
            "domain": "127.0.0.1",
            "path": "/",
            "httpOnly": True,
            "sameSite": "Lax",
        }
    ])


def _inspect(page, screen: str, viewport: str) -> dict:
    return page.evaluate(
        r"""({screen, viewport}) => {
          const body = document.body;
          const text = body ? body.innerText.replace(/\s+/g, ' ').trim() : '';
          const hero = document.querySelector('.v933-public-hero,.v933-client-hero,.v933-page-header,.v944-match-header,.team-center-hero,.competition-center-hero,.player-center-hero,.shark-intelligence-hero');
          const shark = hero ? getComputedStyle(hero, '::before') : null;
          const bodyStyle = body ? getComputedStyle(body) : null;
          const brandMark = document.querySelector('.ns-brand-mark');
          const brandImage = brandMark ? brandMark.querySelector('img') : null;
          const brandStyle = brandMark ? getComputedStyle(brandMark) : null;
          const brandImageStyle = brandImage ? getComputedStyle(brandImage) : null;
          const navigationEntry = performance.getEntriesByType('navigation')[0];
          const brokenImages = Array.from(document.images).filter(img => img.complete && img.naturalWidth === 0).map(img => img.currentSrc || img.src);
          const panels = Array.from(document.querySelectorAll('.v933-panel,.v933-admin-panel,.card'));
          const nestedPanelDepth = panels.reduce((max, node) => {
            let current = node.parentElement;
            let depth = 0;
            while (current) {
              if (current.matches && current.matches('.v933-panel,.v933-admin-panel,.card')) depth += 1;
              current = current.parentElement;
            }
            return Math.max(max, depth);
          }, 0);
          const productSelectors = '[data-sports-priority],.v933-match-card,.v750-live-card,.v944-match-header,.v933-pick-card,.v933-kpi';
          const firstViewportProduct = Array.from(document.querySelectorAll(productSelectors)).some(node => {
            const rect = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return rect.width > 20 && rect.height > 20 && rect.top < innerHeight && rect.bottom > 0 && style.display !== 'none' && style.visibility !== 'hidden';
          });
          const layoutCollisions = [];
          const visible = node => {
            const rect = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return rect.width > 2 && rect.height > 2 && style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) > 0;
          };
          const coverageRatio = nodes => {
            const columns = 12;
            const rows = 8;
            const occupied = new Set();
            for (const node of nodes.filter(visible)) {
              const rect = node.getBoundingClientRect();
              const left = Math.max(0, rect.left);
              const right = Math.min(innerWidth, rect.right);
              const top = Math.max(0, rect.top);
              const bottom = Math.min(innerHeight, rect.bottom);
              if (right <= left || bottom <= top) continue;
              for (let row = 0; row < rows; row += 1) {
                const y = (row + .5) * innerHeight / rows;
                if (y < top || y > bottom) continue;
                for (let column = 0; column < columns; column += 1) {
                  const x = (column + .5) * innerWidth / columns;
                  if (x >= left && x <= right) occupied.add(`${column}:${row}`);
                }
              }
            }
            return Math.round((occupied.size / (columns * rows)) * 1000) / 1000;
          };
          const containerSelector = '.v933-panel,.v933-admin-panel,.v933-kpi,.v933-match-card,.v933-pick-card,.v933-page-header,.v933-plan-card,.v933-quick-action,.v933-profile-card';
          const visibleContainers = Array.from(document.querySelectorAll(containerSelector)).filter(visible);
          const borderedContainers = visibleContainers.filter(node => {
            const style = getComputedStyle(node);
            return style.borderTopStyle !== 'none' && parseFloat(style.borderTopWidth || '0') >= 1;
          }).length;
          const nestedCardDepth = visibleContainers.reduce((max, node) => {
            let depth = 0;
            let current = node.parentElement;
            while (current) {
              if (current.matches && current.matches(containerSelector)) depth += 1;
              current = current.parentElement;
            }
            return Math.max(max, depth);
          }, 0);
          const emptyStateCount = Array.from(document.querySelectorAll('[data-empty-state],.v933-empty-state')).filter(visible).length;
          const visibleKpis = Array.from(document.querySelectorAll('.v933-kpi')).filter(visible).length;
          const realProductNodes = Array.from(document.querySelectorAll('.v933-match-card,.v933-pick-card,.v933-data-table tbody tr,[data-sports-priority]')).filter(visible);
          const emptySensitivePath = ['/picks', '/shark', '/track-record'].includes(location.pathname);
          const emptyDashboardResolved = Boolean(document.querySelector('[data-empty-dashboard="resolved"]'));
          const emptyDashboardFlags = emptySensitivePath && !emptyDashboardResolved && emptyStateCount > 0 && (emptyStateCount > 1 || visibleKpis >= 3)
            ? ['EMPTY_ANALYTICS_DASHBOARD'] : [];
          const compositionNodes = Array.from(document.querySelectorAll('.v933-page-header,.v933-client-hero,.v933-shark-hero,.v933-telegram-hero,.v933-match-card,.v933-pick-card,.v933-kpi,.v933-quick-action,.v933-empty-state,.v933-data-table,.v933-filter-panel,.v933-feature-grid,.v933-linked-state,.v933-link-code,.ns16-journey-steps a,.v933-profile-card,.v933-plan-card,.v933-admin-panel,.ns16-admin-priority,.ns-video-admin-ok,.v944-match-header,.v944-match-sections,.v944-match-panel,.v944-score-widget,.v944-experience-grid,.team-center-hero,.competition-center-hero,.player-center-hero,.team-center-panel,.competition-center-panel,.player-center-panel,.team-center-match-section,.competition-center-match-section,.player-center-match-section')).filter(visible);
          const viewportContentCoverage = coverageRatio(compositionNodes);
          const deadSpaceRelevant = ['/app','/calendar','/live','/picks','/shark','/track-record','/telegram','/profile','/memberships','/admin/dashboard','/admin/founder-dashboard','/admin/automation-center','/admin/growth-command-center','/admin/payments'].includes(location.pathname)
            || /^\/(match|team|competition|player)\//.test(location.pathname);
          const deadSpaceFlags = deadSpaceRelevant && innerWidth >= 1024 && viewportContentCoverage < .28 && !emptyDashboardResolved
            ? ['LARGE_UNJUSTIFIED_EMPTY_REGION'] : [];
          const sportsAboveFoldRatio = coverageRatio(Array.from(document.querySelectorAll('[data-sports-priority],.v933-match-card,.v933-live-card,.v750-live-card,.v944-match-header,.v933-pick-card')));
          const selectorFor = node => {
            if (node.id) return '#' + node.id;
            const classes = Array.from(node.classList || []).slice(0, 3).join('.');
            return node.tagName.toLowerCase() + (classes ? '.' + classes : '');
          };
          const record = (type, node, actual, other=null) => {
            if (layoutCollisions.length >= 60) return;
            const rect = node.getBoundingClientRect();
            layoutCollisions.push({
              type,
              element: selectorFor(node),
              other: other ? selectorFor(other) : '',
              text: (node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180),
              actual,
              rect: {left: Math.round(rect.left), top: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height)},
            });
          };
          const watched = Array.from(document.querySelectorAll([
            'button', 'a.v933-action', '.v933-status-chip', '.v933-filter-tabs a',
            '.v933-bottom-nav a', '.v933-topbar a', '.v933-match-card-header > div',
            '.v933-match-card-header time', '.v933-match-card-actions > *',
            '.v933-page-heading h1', '.v933-section-header h2', '.v933-kpi',
            '.v933-quick-action', '[data-layout-watch]'
          ].join(','))).filter(visible);
          const hasHorizontalScrollContainer = node => {
            let parent = node.parentElement;
            while (parent && parent !== document.body) {
              const parentStyle = getComputedStyle(parent);
              if (['auto', 'scroll'].includes(parentStyle.overflowX) && parent.scrollWidth > parent.clientWidth + 2) return true;
              parent = parent.parentElement;
            }
            return false;
          };
          for (const node of watched) {
            const style = getComputedStyle(node);
            const clippedX = node.scrollWidth > node.clientWidth + 2;
            const clippedY = node.scrollHeight > node.clientHeight + 2;
            const boundedOverflow = ['hidden', 'clip'].includes(style.overflowX) || ['hidden', 'clip'].includes(style.overflowY);
            const compactControl = node.matches('button,a,.v933-status-chip,.v933-filter-tabs a,.v933-match-card-header time');
            if (clippedX || (clippedY && (boundedOverflow || compactControl))) {
              record(node.matches('button,a') ? 'button_clipping' : 'text_clipping', node, 'scroll=' + node.scrollWidth + 'x' + node.scrollHeight + '; client=' + node.clientWidth + 'x' + node.clientHeight);
            }
            if (style.position !== 'fixed') {
              const rect = node.getBoundingClientRect();
              if ((rect.left < -2 || rect.right > innerWidth + 2) && !hasHorizontalScrollContainer(node)) record('viewport_escape', node, 'left=' + Math.round(rect.left) + '; right=' + Math.round(rect.right) + '; viewport=' + innerWidth);
            }
          }
          const cards = Array.from(document.querySelectorAll('.v933-match-card,.v933-pick-card,.v933-kpi,.v933-quick-action,.v933-panel,.v933-admin-panel,.v933-page-header')).filter(visible);
          for (const card of cards) {
            const style = getComputedStyle(card);
            const horizontal = card.scrollWidth > card.clientWidth + 2 && !['auto', 'scroll'].includes(style.overflowX);
            if (horizontal) record('card_overflow', card, 'scroll=' + card.scrollWidth + 'x' + card.scrollHeight + '; client=' + card.clientWidth + 'x' + card.clientHeight);
          }
          const insideVisibleClip = node => {
            const rect = node.getBoundingClientRect();
            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;
            if (centerX < 0 || centerX >= innerWidth || centerY < 0 || centerY >= innerHeight) return false;
            let parent = node.parentElement;
            while (parent && parent !== document.body) {
              const style = getComputedStyle(parent);
              if (['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX) || ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowY)) {
                const parentRect = parent.getBoundingClientRect();
                if (centerX < parentRect.left || centerX > parentRect.right || centerY < parentRect.top || centerY > parentRect.bottom) return false;
              }
              parent = parent.parentElement;
            }
            return true;
          };
          const interactive = Array.from(document.querySelectorAll('a[href],button,input,select,textarea')).filter(node => visible(node) && insideVisibleClip(node));
          const ownsHit = (control, hit) => Boolean(hit && (hit === control || control.contains(hit)));
          const centerHit = rect => document.elementFromPoint(
            Math.max(0, Math.min(innerWidth - 1, rect.left + rect.width / 2)),
            Math.max(0, Math.min(innerHeight - 1, rect.top + rect.height / 2))
          );
          for (let i = 0; i < interactive.length; i += 1) {
            const a = interactive[i];
            const ar = a.getBoundingClientRect();
            for (let j = i + 1; j < interactive.length; j += 1) {
              const b = interactive[j];
              if (a.contains(b) || b.contains(a)) continue;
              const aBottomNav = a.closest('.v933-mobile-bottom-nav,.bottom-nav-clean');
              const bBottomNav = b.closest('.v933-mobile-bottom-nav,.bottom-nav-clean');
              if (Boolean(aBottomNav) !== Boolean(bBottomNav)) continue;
              const br = b.getBoundingClientRect();
              const overlapW = Math.min(ar.right, br.right) - Math.max(ar.left, br.left);
              const overlapH = Math.min(ar.bottom, br.bottom) - Math.max(ar.top, br.top);
              if (overlapW > 2 && overlapH > 2) {
                const aHit = centerHit(ar);
                const bHit = centerHit(br);
                const aBlockedByB = !ownsHit(a, aHit) && ownsHit(b, aHit);
                const bBlockedByA = !ownsHit(b, bHit) && ownsHit(a, bHit);
                if (aBlockedByB || bBlockedByA) record(
                  'interactive_overlap',
                  a,
                  'overlap=' + Math.round(overlapW) + 'x' + Math.round(overlapH) + '; blocked=' + (aBlockedByB ? 'first' : 'second'),
                  b
                );
              }
            }
          }
          const bg = bodyStyle ? bodyStyle.backgroundImage : '';
          const sharkImage = shark ? shark.backgroundImage : '';
          const sharkWidth = shark ? parseFloat(shark.width || '0') : 0;
          const sharkOpacity = shark ? parseFloat(shark.opacity || '0') : 0;
          const sharkRatio = innerWidth ? sharkWidth / innerWidth : 0;
          const sharkAssetOk = /nemesis-shark-atmosphere\.svg/.test(sharkImage);
          const sharkGeometryOk = sharkRatio >= .16 && sharkRatio <= (innerWidth <= 767 ? .78 : .55) && sharkOpacity >= .18 && sharkOpacity <= .98;
          const backgroundOk = /gradient/.test(bg) && !/^none$/i.test(bg);
          const lineup = document.querySelector('[data-lineups-contract]');
          const summary = document.querySelector('[data-summary-contract]');
          const rightsNodes = Array.from(document.querySelectorAll('[data-rights-decision]')).filter(node => {
            const rect = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
          });
          const safeRights = new Set(['APPROVED', 'ATTRIBUTION_REQUIRED']);
          return {
            screen,
            viewport,
            path: location.pathname,
            title: document.title,
            visible_text: text,
            text_length: text.length,
            page_ready_ms: navigationEntry ? Math.round(navigationEntry.domContentLoadedEventEnd - navigationEntry.startTime) : null,
            horizontal_overflow: document.documentElement.scrollWidth > innerWidth + 1,
            overflow_actual: `${document.documentElement.scrollWidth}/${innerWidth}`,
            broken_images: brokenImages,
            first_viewport_product: firstViewportProduct,
            nested_panel_depth: nestedPanelDepth,
            composition: {
              dead_space_flags: deadSpaceFlags,
              empty_dashboard_flags: emptyDashboardFlags,
              bordered_containers: borderedContainers,
              nested_card_depth: nestedCardDepth,
              empty_state_count: emptyStateCount,
              real_product_nodes: realProductNodes.length,
              viewport_content_coverage: viewportContentCoverage,
              sports_above_fold_ratio: sportsAboveFoldRatio,
            },
            layout_collisions: layoutCollisions,
            brand: {
              asset: brandImage ? (brandImage.currentSrc || brandImage.src) : '',
              mark_width: brandStyle ? brandStyle.width : '',
              mark_height: brandStyle ? brandStyle.height : '',
              image_width: brandImageStyle ? brandImageStyle.width : '',
              image_height: brandImageStyle ? brandImageStyle.height : '',
              background: brandStyle ? brandStyle.backgroundImage : '',
              background_color: brandStyle ? brandStyle.backgroundColor : '',
              border: brandStyle ? brandStyle.border : '',
              border_radius: brandStyle ? brandStyle.borderRadius : '',
              box_shadow: brandStyle ? brandStyle.boxShadow : '',
              overflow: brandStyle ? brandStyle.overflow : '',
            },
            shark: {
              asset: sharkImage,
              width_px: sharkWidth,
              width_ratio: Math.round(sharkRatio * 1000) / 1000,
              opacity: sharkOpacity,
              classification: sharkAssetOk && sharkGeometryOk ? 'MINOR_GAP' : 'MAJOR_GAP',
              evidence: `asset=${sharkImage}; ratio=${sharkRatio.toFixed(3)}; opacity=${sharkOpacity}`,
            },
            background: {
              classification: backgroundOk ? 'MINOR_GAP' : 'MAJOR_GAP',
              evidence: `background=${bg.slice(0, 420)}`,
            },
            live_contract: {
              confirmed: Number(document.querySelector('[data-sports-live-confirmed]')?.getAttribute('data-sports-live-confirmed') || 0),
              displayed: (() => {
                const candidates = Array.from(document.querySelectorAll('.v933-hero-proof span,.v933-client-hero-meta span,.sports-priority-kpis .v933-kpi'));
                for (const node of candidates) {
                  const value = (node.innerText || '').replace(/\s+/g, ' ').trim();
                  if (/en directo/i.test(value)) {
                    const match = value.match(/\d+/);
                    if (match) return Number(match[0]);
                  }
                }
                return 0;
              })(),
              ft_rendered_live: Array.from(document.querySelectorAll('[data-match-status],.v933-status-chip,.v933-live-card')).filter(node => {
                const value = (node.innerText || '').toUpperCase();
                return /(?:FT|FINALIZADO|FINISHED)/.test(value) && /(?:LIVE|EN DIRECTO)/.test(value);
              }).length,
            },
            match_truth: Array.from(document.querySelectorAll('[data-v934-match-id][data-canonical-status],[data-match-id][data-canonical-status]')).map(node => ({
              match_id: node.getAttribute('data-v934-match-id') || node.getAttribute('data-match-id') || '',
              canonical_status: (node.getAttribute('data-canonical-status') || '').toUpperCase(),
              is_live: node.getAttribute('data-canonical-live') === 'true',
            })),
            competition_truth: Array.from(document.querySelectorAll('[data-v934-match-id][data-canonical-competition-id]')).map(node => ({
              match_id: node.getAttribute('data-v934-match-id') || '',
              competition_id: node.getAttribute('data-canonical-competition-id') || '',
              contract: node.getAttribute('data-competition-identity-contract') || '',
            })),
            temporal_truth: Array.from(document.querySelectorAll('[data-match-temporal-context]')).map(node => {
              const owner = node.closest('[data-v934-match-id],[data-match-id]');
              return {
                match_id: owner?.getAttribute('data-v934-match-id') || owner?.getAttribute('data-match-id') || '',
                datetime: node.getAttribute('datetime') || '',
                label: (node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim(),
                contract: node.getAttribute('data-match-temporal-context') || '',
              };
            }),
            temporal_truth: Array.from(document.querySelectorAll('[data-match-temporal-context]')).map(node => {
              const owner = node.closest('[data-v934-match-id],[data-match-id]');
              return {
                match_id: owner?.getAttribute('data-v934-match-id') || owner?.getAttribute('data-match-id') || '',
                datetime: node.getAttribute('datetime') || '',
                label: (node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim(),
                contract: node.getAttribute('data-match-temporal-context') || '',
              };
            }),
            sports_knowledge: {
              lineup_state: lineup?.getAttribute('data-lineup-state') || 'not_observed',
              lineup_confirmed: lineup?.getAttribute('data-lineup-state') === 'confirmed',
              lineup_player_links: document.querySelectorAll("[data-match-region='lineups'] a[data-entity-contract='player']").length,
              summary_contract: summary?.getAttribute('data-summary-contract') || '',
              summary_ai_calls: Number(summary?.getAttribute('data-summary-ai-calls') || 0),
              summary_unsupported_claims: Number(summary?.getAttribute('data-summary-unsupported-claims') || 0),
              authorized_video_visible: document.querySelectorAll("[data-match-region='authorized-video'] [data-rights-decision]").length,
              unsafe_media_visible: rightsNodes.filter(node => !safeRights.has((node.getAttribute('data-rights-decision') || '').toUpperCase())).length,
            },
          };
        }""",
        {"screen": screen, "viewport": viewport},
    )


def _exact_click(page, *, zone: str, label: str, expected_path: str, screen: str, viewport: str, screenshot: str) -> dict:
    current = urlparse(page.url)
    page.goto(f"{current.scheme}://{current.netloc}/app", wait_until="domcontentloaded")
    locator = page.locator(f"[data-nav-zone='{zone}'] a").filter(has_text=re.compile(rf"^{re.escape(label)}$", re.I)).first
    try:
        locator.wait_for(state="visible", timeout=5000)
        hit = locator.evaluate(
            """node => {
              const rect = node.getBoundingClientRect();
              const top = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
              return {
                ok: !!top && (top === node || node.contains(top)),
                target: node.tagName + ':' + (node.getAttribute('href') || ''),
                top: top ? top.tagName + ':' + (top.closest('a')?.getAttribute('href') || '') : 'none'
              };
            }"""
        )
        locator.click(timeout=6000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        actual = urlparse(page.url).path
        return {
            "screen": screen,
            "viewport": viewport,
            "element": label,
            "expected_path": expected_path,
            "actual_path": actual,
            "clicked": True,
            "hit_target": bool(hit.get("ok")),
            "http_status": 200,
            "page_ready": bool(page.locator("main").count()),
            "screenshot": screenshot,
            "evidence": f"Clic exacto validado con elementFromPoint: target={hit.get('target')}; top={hit.get('top')}.",
        }
    except Exception as exc:
        return {
            "screen": screen,
            "viewport": viewport,
            "element": label,
            "expected_path": expected_path,
            "actual_path": urlparse(page.url).path,
            "clicked": False,
            "hit_target": False,
            "http_status": 0,
            "page_ready": False,
            "screenshot": screenshot,
            "evidence": f"{type(exc).__name__}: {str(exc)[:260]}",
        }


def _journey_step(page, route: str, selector: str, expected_prefix: str) -> dict:
    page.goto(route, wait_until="domcontentloaded")
    target = page.locator(selector).first
    try:
        target.wait_for(state="visible", timeout=5000)
        target.click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        actual = urlparse(page.url).path
        return {"route": route, "selector": selector, "expected": expected_prefix, "actual": actual, "pass": actual.startswith(expected_prefix)}
    except Exception as exc:
        return {"route": route, "selector": selector, "expected": expected_prefix, "actual": urlparse(page.url).path, "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:220]}"}


def _section_anchor_journey(page, route: str, section: str) -> dict:
    selector = f"[data-match-section-link='{section}']"
    expected_fragment = f"match-section-{section}"
    try:
        response = page.goto(route, wait_until="domcontentloaded", timeout=10000)
        target = page.locator(selector).first
        target.wait_for(state="visible", timeout=5000)
        target.click(timeout=5000)
        fragment = urlparse(page.url).fragment
        section_visible = page.locator(f"#{expected_fragment}").is_visible()
        return {
            "step": f"match_section_{section}",
            "route": route,
            "selector": selector,
            "expected": f"#{expected_fragment}",
            "actual": f"#{fragment}",
            "http_status": response.status if response else 0,
            "pass": bool(response and response.status < 500 and fragment == expected_fragment and section_visible),
        }
    except Exception as exc:
        return {
            "step": f"match_section_{section}",
            "route": route,
            "selector": selector,
            "expected": f"#{expected_fragment}",
            "actual": f"#{urlparse(page.url).fragment}",
            "pass": False,
            "error": f"{type(exc).__name__}: {str(exc)[:220]}",
        }


def _page_ready_journey(page, route: str, label: str) -> dict:
    try:
        response = page.goto(route, wait_until="domcontentloaded", timeout=10000)
        ready = bool(page.locator("main").count()) and bool(page.locator("h1").count())
        return {"journey": label, "route": route, "http_status": response.status if response else 0, "page_ready": ready, "pass": bool(response and response.status < 500 and ready)}
    except Exception as exc:
        return {"journey": label, "route": route, "http_status": 0, "page_ready": False, "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:220]}"}


def _sports_knowledge_evidence_journey(page, route: str) -> dict:
    try:
        response = page.goto(route, wait_until="domcontentloaded", timeout=10000)
        summary = page.locator("[data-summary-contract='NEMESIS-FACTUAL-MATCH-SUMMARIES-V1']").first
        video = page.locator("[data-match-region='authorized-video'] [data-rights-decision]").first
        summary_ready = bool(summary.count() and summary.is_visible())
        video_ready = bool(video.count() and video.is_visible())
        return {
            "journey": "sports_knowledge_summary_or_video",
            "route": route,
            "expected": "Resumen factual o vídeo oficial autorizado visible.",
            "actual": "AUTHORIZED_VIDEO" if video_ready else "FACTUAL_SUMMARY" if summary_ready else "NO_EVIDENCE_SURFACE",
            "http_status": response.status if response else 0,
            "pass": bool(response and response.status < 500 and (summary_ready or video_ready)),
        }
    except Exception as exc:
        return {"journey": "sports_knowledge_summary_or_video", "route": route, "expected": "Resumen factual o vídeo oficial autorizado visible.", "actual": "ERROR", "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:220]}"}


def _golden_journey(name: str, steps: list[dict]) -> dict:
    passed = bool(steps) and all(step.get("pass") is True for step in steps)
    return {
        "journey": name,
        "pass": passed,
        "steps_passed": sum(1 for step in steps if step.get("pass") is True),
        "steps_total": len(steps),
        "steps": steps,
        "actual": "COMPLETED" if passed else "FAILED_STEP",
    }


def _public_golden_journey(page, base_url: str, qa_password: str) -> dict:
    steps: list[dict] = []
    page.context.clear_cookies()
    try:
        response = page.goto(base_url + "/landing", wait_until="domcontentloaded", timeout=10000)
        register_link = page.locator("a[href^='/registro']").first
        register_link.click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        registration_opened = urlparse(page.url).path == "/registro"
        steps.append({"step": "landing_to_registration", "pass": bool(response and response.status < 500 and registration_opened), "actual": urlparse(page.url).path})
        page.locator("input[name='name']").fill("Persona QA")
        page.locator("input[name='username']").fill("persona_qa")
        page.locator("input[name='email']").fill("persona-qa@example.invalid")
        page.locator("input[name='password']").fill(qa_password)
        page.get_by_role("button", name=re.compile(r"Crear cuenta", re.I)).click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        registered = urlparse(page.url).path == "/app"
        steps.append({"step": "registration_to_home", "pass": registered, "actual": urlparse(page.url).path, "database": "TEMP_QA_ONLY"})
        steps.append(_journey_step(page, base_url + "/app", "[data-nav-zone='client-desktop'] a[href='/calendar']", "/calendar"))
        steps.append(_journey_step(page, base_url + "/calendar", "a[href^='/match/']", "/match/"))
        steps.append(_journey_step(page, base_url + "/match/m-1", "[data-nav-zone='client-desktop'] a[href='/app']", "/app"))
    except Exception as exc:
        steps.append({"step": "public_exception", "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:240]}"})
    return _golden_journey("golden_public", steps)


def _sports_golden_journey(page, base_url: str) -> dict:
    steps = [
        _journey_step(page, base_url + "/app", "[data-nav-zone='client-desktop'] a[href='/live']", "/live"),
        _live_center_journey(page, base_url + "/live"),
        _journey_step(page, base_url + "/app", "a[href^='/match/']", "/match/"),
        _section_anchor_journey(page, base_url + "/match/m-1", "lineups"),
        _journey_step(page, base_url + "/match/m-1", "[data-match-region='lineups'] a[href^='/player/']", "/player/"),
        _journey_step(page, base_url + "/player/101", "a[href^='/team/']", "/team/"),
        _journey_step(page, base_url + "/team/Club%20Norte", "a[href^='/competition/']", "/competition/"),
        _journey_step(page, base_url + "/competition/140", "a[href^='/match/']", "/match/"),
        _section_anchor_journey(page, base_url + "/match/m-1", "timeline"),
        _section_anchor_journey(page, base_url + "/match/m-1", "stats"),
        _section_anchor_journey(page, base_url + "/match/m-1", "story"),
        _section_anchor_journey(page, base_url + "/match/m-1", "video"),
        _sports_knowledge_evidence_journey(page, base_url + "/match/m-1"),
        _journey_step(page, base_url + "/match/m-1", "a[href^='/shark?match=']", "/shark"),
    ]
    return _golden_journey("golden_sports_knowledge", steps)


def _live_center_journey(page, route: str) -> dict:
    try:
        response = page.goto(route, wait_until="domcontentloaded", timeout=10000)
        match = page.locator("a[href^='/match/']:visible").first
        if match.count():
            match.click(timeout=5000)
            page.wait_for_load_state("domcontentloaded", timeout=8000)
            actual = urlparse(page.url).path
            return {"journey": "live_center", "route": route, "expected": "/match/ or honest empty state", "actual": actual, "pass": actual.startswith("/match/")}
        text = page.locator("main").inner_text(timeout=5000)
        honest_empty = "No hay partidos para este estado" in text or "Sin directo destacado" in text
        return {
            "journey": "live_center",
            "route": route,
            "expected": "/match/ or honest empty state",
            "actual": "HONEST_EMPTY_STATE" if honest_empty else "NO_MATCH_WITHOUT_EMPTY_STATE",
            "http_status": response.status if response else 0,
            "pass": bool(response and response.status < 500 and honest_empty),
        }
    except Exception as exc:
        return {"journey": "live_center", "route": route, "expected": "/match/ or honest empty state", "actual": "ERROR", "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:220]}"}


def _favorite_journey(page, base_url: str) -> dict:
    page.goto(base_url + "/favorites", wait_until="domcontentloaded")
    try:
        details = page.locator("details#add-favorite-manual")
        details.locator("summary").click(timeout=5000)
        form = details.locator("form[action='/favorites']")
        form.locator("select[name='kind']").select_option("match")
        form.locator("input[name='value']").fill("m-1")
        form.locator("input[name='label']").fill("Partido QA")
        form.get_by_role("button", name="Guardar favorito").click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        added = page.locator(".favorite-item").filter(has_text="Partido QA").count() == 1
        page.locator("a[href='/calendar']").first.click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        entity = page.locator("a[href='/match/m-1']").first
        entity.wait_for(state="visible", timeout=5000)
        entity.click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        opened = urlparse(page.url).path == "/match/m-1"
        page.goto(base_url + "/favorites", wait_until="domcontentloaded")
        remove_form = page.locator(".favorite-item").filter(has_text="Partido QA").locator("form[action='/favorites']")
        remove_form.get_by_role("button", name="Quitar").click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        removed = page.locator(".favorite-item").filter(has_text="Partido QA").count() == 0
        return {"journey": "golden_favorites", "added": added, "opened": opened, "removed": removed, "pass": added and opened and removed, "database": "TEMP_QA_ONLY"}
    except Exception as exc:
        return {"journey": "golden_favorites", "added": False, "opened": False, "removed": False, "pass": False, "database": "TEMP_QA_ONLY", "error": f"{type(exc).__name__}: {str(exc)[:240]}"}


def _shark_golden_journey(page, base_url: str) -> dict:
    steps = [
        _journey_step(page, base_url + "/app", "a[href^='/match/']", "/match/"),
        _journey_step(page, base_url + "/match/m-1", "a[href^='/shark?match=']", "/shark"),
    ]
    try:
        page.go_back(wait_until="domcontentloaded", timeout=8000)
        steps.append({"step": "shark_back_to_match", "actual": urlparse(page.url).path, "pass": urlparse(page.url).path == "/match/m-1"})
    except Exception as exc:
        steps.append({"step": "shark_back_to_match", "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
    return _golden_journey("golden_shark", steps)


def _picks_golden_journey(page, base_url: str) -> dict:
    steps: list[dict] = []
    try:
        response = page.goto(base_url + "/picks", wait_until="domcontentloaded", timeout=10000)
        match = page.locator("a[href^='/match/']:visible").first
        if match.count():
            match.click(timeout=5000)
            page.wait_for_load_state("domcontentloaded", timeout=8000)
            steps.append({"step": "pick_to_match", "actual": urlparse(page.url).path, "pass": urlparse(page.url).path.startswith("/match/")})
        else:
            text = page.locator("main").inner_text(timeout=5000)
            honest_empty = "Sin pick real publicable" in text or "No hay picks" in text or "Todavía no hay picks" in text
            steps.append({"step": "picks_honest_empty", "http_status": response.status if response else 0, "actual": "HONEST_EMPTY_STATE" if honest_empty else "MISSING_EMPTY_STATE", "pass": bool(response and response.status < 500 and honest_empty)})
    except Exception as exc:
        steps.append({"step": "picks_exception", "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:220]}"})
    return _golden_journey("golden_picks", steps)


def _account_golden_journey(page, base_url: str, qa_password: str) -> dict:
    steps: list[dict] = []
    page.context.clear_cookies()
    try:
        page.goto(base_url + "/cliente-login", wait_until="domcontentloaded", timeout=10000)
        page.locator("input[name='login']").fill("cliente_qa")
        page.locator("input[name='password']").fill(qa_password)
        page.get_by_role("button", name="Entrar", exact=True).click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        steps.append({"step": "client_login", "actual": urlparse(page.url).path, "pass": urlparse(page.url).path == "/app"})
        steps.append(_journey_step(page, base_url + "/app", "[data-nav-zone='client-desktop'] a[href='/profile']", "/profile"))
        for label, href, expected in (
            ("security", "/password-reset", "/forgot-password"),
            ("preferences", "/alertas", "/alertas"),
            ("telegram", "/telegram", "/telegram"),
            ("support", "/support", "/support"),
        ):
            step = _journey_step(page, base_url + "/profile", f"a[href='{href}']", expected)
            step["step"] = label
            steps.append(step)
        page.goto(base_url + "/profile", wait_until="domcontentloaded")
        page.locator("a[href='/logout']").first.click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        steps.append({"step": "logout", "actual": urlparse(page.url).path, "pass": urlparse(page.url).path in {"/", "/cliente-login"}})
    except Exception as exc:
        steps.append({"step": "account_exception", "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:240]}"})
    return _golden_journey("golden_account", steps)


def _admin_golden_journey(page, base_url: str, qa_password: str) -> dict:
    steps: list[dict] = []
    # Cancel client-page requests before clearing its session. A late response can
    # otherwise restore the old cookie and invalidate the admin form CSRF token.
    page.goto("about:blank", wait_until="domcontentloaded", timeout=5000)
    page.context.clear_cookies()
    try:
        page.goto(base_url + "/admin-login", wait_until="domcontentloaded", timeout=10000)
        page.locator("input[name='login']").fill("admin_qa")
        page.locator("input[name='password']").fill(qa_password)
        page.get_by_role("button", name="Entrar como admin").click(timeout=5000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        steps.append({"step": "admin_login", "actual": urlparse(page.url).path, "pass": urlparse(page.url).path.startswith("/admin/") and urlparse(page.url).path != "/admin-login"})
        founder_response = page.goto(base_url + "/admin/founder-dashboard", wait_until="domcontentloaded", timeout=10000)
        steps.append({"step": "founder_authenticated", "actual": urlparse(page.url).path, "pass": bool(founder_response and founder_response.status < 500 and urlparse(page.url).path == "/admin/founder-dashboard")})
        for label, selector, expected in (
            ("product_review", "a[href='/admin/product-review-center']", "/admin/product-review-center"),
            ("evidence", "a[href='/admin/sentinel-issues']", "/admin/sentinel-issues"),
            ("prepared_for_codex", "a[href='/admin/sentinel-codex-outbox']", "/admin/sentinel-codex-outbox"),
        ):
            step = _journey_step(page, base_url + "/admin/founder-dashboard", selector, expected)
            step["step"] = label
            steps.append(step)
        for label, route in (("operations", "/admin/operations-center"), ("growth", "/admin/founder-dashboard#growth-revenue"), ("continuous_evolution", "/admin/founder-dashboard#continuous-evolution")):
            response = page.goto(base_url + route, wait_until="domcontentloaded", timeout=10000)
            fragment = urlparse(route).fragment
            target_visible = not fragment or page.locator(f"#{fragment}").count() == 1
            response_ok = response is None or response.status < 500
            steps.append({"step": label, "actual": page.url, "pass": bool(response_ok and "/admin-login" not in page.url and target_visible), "navigation": "AUTHENTICATED_SAFE_GET"})
    except Exception as exc:
        steps.append({"step": "admin_exception", "pass": False, "error": f"{type(exc).__name__}: {str(exc)[:240]}"})
    return _golden_journey("golden_admin", steps)


def _client_admin_separation_journey(page, base_url: str, app_module) -> dict:
    page.goto("about:blank", wait_until="domcontentloaded", timeout=5000)
    page.context.clear_cookies()
    _set_role_cookie(page.context, app_module, "client")
    try:
        response = page.goto(base_url + "/admin/founder-dashboard", wait_until="domcontentloaded", timeout=10000)
        actual = urlparse(page.url).path
        passed = actual == "/admin-login"
        return {
            "journey": "client_admin_separation",
            "route": "/admin/founder-dashboard",
            "expected": "/admin-login",
            "actual": actual,
            "http_status": response.status if response else 0,
            "pass": passed,
            "evidence": "Sesion cliente real de QA rechazada por la proteccion backend." if passed else "La sesion cliente alcanzo una ruta administrativa.",
        }
    except Exception as exc:
        return {
            "journey": "client_admin_separation",
            "route": "/admin/founder-dashboard",
            "expected": "/admin-login",
            "actual": urlparse(page.url).path,
            "pass": False,
            "error": f"{type(exc).__name__}: {str(exc)[:220]}",
        }


def _sports_priority_regression(app_module) -> dict:
    now_value = app_module.datetime.now(app_module.TZ).replace(hour=12, minute=0, second=0, microsecond=0)

    def match(match_id: str, competition: str, country: str, home: str, away: str, kickoff: str) -> dict:
        return {
            "id": match_id,
            "match_id": match_id,
            "match_date": app_module.today_iso(),
            "kickoff_time": kickoff,
            "home_team": home,
            "away_team": away,
            "competition_name": competition,
            "country": country,
            "source": "qa-regression-fixture",
            "status": "NS",
            "v935_lifecycle": "UPCOMING",
            "v935_surface": {"home": True, "calendar": True, "live": False},
        }

    matches = [
        match("k-league-2", "South Korean K League 2", "South Korea", "Busan", "Seoul E-Land", "17:00"),
        match("chinese-super-league", "Chinese Super League", "China", "Shanghai", "Beijing", "17:15"),
        match("bayern-stuttgart", "Bundesliga", "Germany", "Bayern Munich", "Stuttgart", "18:30"),
        match("lille-psg", "Ligue 1", "France", "Lille", "Paris Saint-Germain", "18:45"),
        match("milan-venezia", "Serie A", "Italy", "AC Milan", "Venezia", "18:45"),
    ]
    ranked = app_module.sort_matches_by_sports_relevance(
        matches,
        "home",
        pick_ids={"k-league-2", "chinese-super-league"},
        now_value=now_value,
    )
    order = [item["id"] for item in ranked]
    important = ("bayern-stuttgart", "lille-psg", "milan-venezia")
    low_priority = ("k-league-2", "chinese-super-league")
    passed = all(order.index(elite) < order.index(low) for elite in important for low in low_priority)
    return {
        "status": "PASS" if passed else "FAIL",
        "order": order,
        "external_calls": 0,
        "evidence": " > ".join(order),
    }


def _cross_surface_live_truth_evidence(captures: list[dict]) -> dict:
    """Compare the same canonical match across rendered sports surfaces."""
    sports_surfaces = {"home", "public_home", "partidos", "directo", "match", "team", "competition", "player", "picks", "shark"}
    by_match: dict[str, dict[str, dict]] = {}
    for capture in captures:
        surface = str(capture.get("key") or "")
        if surface not in sports_surfaces:
            continue
        for item in capture.get("match_truth") or []:
            match_id = str(item.get("match_id") or "").strip()
            status = str(item.get("canonical_status") or "").strip().upper()
            if not match_id or not status:
                continue
            by_match.setdefault(match_id, {})[surface] = {
                "canonical_status": status,
                "is_live": bool(item.get("is_live")),
            }

    compared = {match_id: surfaces for match_id, surfaces in by_match.items() if len(surfaces) >= 2}
    mismatches = []
    for match_id, surfaces in sorted(compared.items()):
        truths = {(item["canonical_status"], item["is_live"]) for item in surfaces.values()}
        if len(truths) > 1:
            mismatches.append({"match_id": match_id, "surfaces": surfaces})
    return {
        "observed": bool(compared),
        "pass": bool(compared) and not mismatches,
        "matches_compared": len(compared),
        "mismatches": mismatches,
    }


def _cross_surface_competition_identity_evidence(captures: list[dict]) -> dict:
    """Require one canonical competition id for the same rendered match."""
    sports_surfaces = {"home", "public_home", "partidos", "directo", "match", "team", "competition", "player", "picks", "shark"}
    by_match: dict[str, dict[str, str]] = {}
    for capture in captures:
        surface = str(capture.get("key") or "")
        if surface not in sports_surfaces:
            continue
        for item in capture.get("competition_truth") or []:
            match_id = str(item.get("match_id") or "").strip()
            competition_id = str(item.get("competition_id") or "").strip()
            if match_id and competition_id:
                by_match.setdefault(match_id, {})[surface] = competition_id
    compared = {match_id: surfaces for match_id, surfaces in by_match.items() if len(surfaces) >= 2}
    mismatches = []
    for match_id, surfaces in sorted(compared.items()):
        if len(set(surfaces.values())) > 1:
            mismatches.append({"match_id": match_id, "surfaces": surfaces})
    return {
        "observed": bool(compared),
        "pass": bool(compared) and not mismatches,
        "matches_compared": len(compared),
        "mismatches": mismatches,
    }


def _cross_surface_temporal_evidence(captures: list[dict]) -> dict:
    """Verify that rendered match dates retain the canonical Madrid instant."""
    sports_surfaces = {"home", "public_home", "partidos", "directo", "match", "team", "competition", "player", "picks", "shark", "track_record"}
    by_match: dict[str, dict[str, str]] = {}
    checked = 0
    missing = 0
    ambiguous = 0
    madrid_values: list[str] = []
    context_re = re.compile(r"(?:hoy|mañana|lunes|martes|miércoles|jueves|viernes|sábado|domingo|\d{1,2}[/:.-]|\d{1,2}:\d{2}|final|directo|aplazado|cancelado)", re.I)
    for capture in captures:
        surface = str(capture.get("key") or "")
        if surface not in sports_surfaces:
            continue
        for item in capture.get("temporal_truth") or []:
            checked += 1
            label = str(item.get("label") or "").strip()
            instant = str(item.get("datetime") or "").strip()
            match_id = str(item.get("match_id") or "").strip()
            if not label or re.search(r"(?:fecha pendiente|fecha no disponible|no disponible)", label, re.I):
                missing += 1
            elif not context_re.search(label):
                ambiguous += 1
            if instant:
                madrid_values.append(instant)
                if match_id:
                    by_match.setdefault(match_id, {})[surface] = instant
    compared = {match_id: surfaces for match_id, surfaces in by_match.items() if len(surfaces) >= 2}
    mismatches = [
        {"match_id": match_id, "surfaces": surfaces}
        for match_id, surfaces in sorted(compared.items())
        if len(set(surfaces.values())) > 1
    ]
    madrid_time = bool(madrid_values) and all(re.search(r"(?:[+-]01:00|[+-]02:00)$", value) for value in madrid_values)
    return {
        "observed": checked > 0 and bool(compared),
        "checked_cards": checked,
        "missing_cards": missing,
        "ambiguous_cards": ambiguous,
        "cross_surface_consistent": bool(compared) and not mismatches,
        "matches_compared": len(compared),
        "mismatches": mismatches,
        "madrid_time": madrid_time,
    }


def _cross_surface_temporal_evidence(captures: list[dict]) -> dict:
    """Verify that rendered match dates retain the canonical Madrid instant."""
    sports_surfaces = {"home", "public_home", "partidos", "directo", "match", "team", "competition", "player", "picks", "shark", "track_record"}
    by_match: dict[str, dict[str, str]] = {}
    checked = 0
    missing = 0
    ambiguous = 0
    madrid_values: list[str] = []
    context_re = re.compile(r"(?:hoy|mañana|lunes|martes|miércoles|jueves|viernes|sábado|domingo|\d{1,2}[/:.-]|\d{1,2}:\d{2}|final|directo|aplazado|cancelado)", re.I)
    for capture in captures:
        surface = str(capture.get("key") or "")
        if surface not in sports_surfaces:
            continue
        for item in capture.get("temporal_truth") or []:
            checked += 1
            label = str(item.get("label") or "").strip()
            instant = str(item.get("datetime") or "").strip()
            match_id = str(item.get("match_id") or "").strip()
            if not label or re.search(r"(?:fecha pendiente|fecha no disponible|no disponible)", label, re.I):
                missing += 1
            elif not context_re.search(label):
                ambiguous += 1
            if instant:
                madrid_values.append(instant)
                if match_id:
                    by_match.setdefault(match_id, {})[surface] = instant
    compared = {match_id: surfaces for match_id, surfaces in by_match.items() if len(surfaces) >= 2}
    mismatches = [
        {"match_id": match_id, "surfaces": surfaces}
        for match_id, surfaces in sorted(compared.items())
        if len(set(surfaces.values())) > 1
    ]
    madrid_time = bool(madrid_values) and all(re.search(r"(?:[+-]01:00|[+-]02:00)$", value) for value in madrid_values)
    return {
        "observed": checked > 0 and bool(compared),
        "checked_cards": checked,
        "missing_cards": missing,
        "ambiguous_cards": ambiguous,
        "cross_surface_consistent": bool(compared) and not mismatches,
        "matches_compared": len(compared),
        "mismatches": mismatches,
        "madrid_time": madrid_time,
    }


def _reference_map() -> dict[str, str]:
    path = ROOT / "reference_images" / "reference_manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    result = {str(item.get("screen_target")): str(item.get("reference_file") or item.get("filename")) for item in manifest.get("items") or []}
    if "/membresias" in result:
        result["/memberships"] = result["/membresias"]
    return result


def _reference_similarity(screenshot: Path, reference_file: str) -> dict:
    """Compare rendered composition and palette without requiring identical data."""
    if not reference_file:
        return {"classification": "NOT_APPLICABLE", "score": None, "reference_file": ""}
    reference = (ROOT / reference_file).resolve()
    try:
        from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat

        with Image.open(screenshot) as current_image, Image.open(reference) as reference_image:
            size = (64, 36)
            current = ImageOps.fit(current_image.convert("RGB"), size, method=Image.Resampling.LANCZOS)
            expected = ImageOps.fit(reference_image.convert("RGB"), size, method=Image.Resampling.LANCZOS)
            diff = ImageStat.Stat(ImageChops.difference(current, expected))
            pixel_score = max(0.0, 1.0 - (sum(diff.mean) / 3.0 / 255.0))

            current_hist = current.resize((16, 9)).histogram()
            expected_hist = expected.resize((16, 9)).histogram()
            histogram_total = max(1, sum(current_hist))
            histogram_delta = sum(abs(left - right) for left, right in zip(current_hist, expected_hist))
            palette_score = max(0.0, 1.0 - histogram_delta / (2.0 * histogram_total))

            current_edges = ImageStat.Stat(current.filter(ImageFilter.FIND_EDGES).convert("L")).mean[0]
            expected_edges = ImageStat.Stat(expected.filter(ImageFilter.FIND_EDGES).convert("L")).mean[0]
            edge_score = max(0.0, 1.0 - abs(current_edges - expected_edges) / 255.0)
            score = round((pixel_score * 0.45) + (palette_score * 0.4) + (edge_score * 0.15), 4)
    except (OSError, ValueError, ImportError) as exc:
        return {
            "classification": "NOT_OBSERVED",
            "score": None,
            "reference_file": reference_file,
            "evidence": f"{type(exc).__name__}: {str(exc)[:180]}",
        }
    classification = "MATCH" if score >= 0.82 else "MINOR_GAP" if score >= 0.58 else "MAJOR_GAP" if score >= 0.42 else "REBUILD_REQUIRED"
    return {
        "classification": classification,
        "score": score,
        "reference_file": reference_file,
        "evidence": f"coarse_composition_similarity={score}; reference={reference_file}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "browser_qa" / "AUTONOMOUS_PRODUCT_QA"))
    parser.add_argument("--production-sha", default="LOCAL")
    parser.add_argument("--evidence-origin", default="LOCAL_QA", choices=["LOCAL_QA", "REAL_PRODUCTION_OBSERVATION", "SIMULATED_TEST"])
    parser.add_argument("--scope", default="full", choices=["critical", "full"])
    parser.add_argument("--trigger", default="AUTONOMOUS_BROWSER_QA")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    db_path = ROOT / "data" / "local_dev" / "nemesis_autonomous_product_qa.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    os.environ.update({
        "DB_PATH": str(db_path),
        "NEMESIS_LOCAL_DB_NAME": db_path.name,
        "SECRET_KEY": "autonomous-product-qa-local-secret",
        "RUN_STARTUP_SCHEDULER_NOW": "0",
        "NEMESIS_LOCAL_SAFE_MODE": "1",
        "NEMESIS_OFFLINE_MODE": "1",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
        "STRIPE_SECRET_KEY": "",
        "STRIPE_WEBHOOK_SECRET": "",
        "OPENAI_API_KEY": "",
    })
    qa_password = secrets.token_urlsafe(24)
    seed_database(db_path)
    _seed_extra(db_path, qa_password)

    import app as app_module
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app_module.DB_PATH = str(db_path)
    app_module.app.config.update(TESTING=True)
    app_module._SEEDED_DB_PATH = str(db_path)
    app_module._SEEDING_DB_PATH = None
    app_module.APP_INITIALIZED = True
    _seed_extra(db_path, qa_password)
    server = make_server("127.0.0.1", 0, app_module.app)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    captures: list[dict] = []
    navigation_clicks: list[dict] = []
    journeys: list[dict] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    provider_calls: list[str] = []
    reference_files = _reference_map()
    selected_screens = SCREENS if args.scope == "full" else [item for item in SCREENS if item[0] in CRITICAL_SCREEN_KEYS]
    started_at = datetime.now(MADRID).replace(microsecond=0)
    started = started_at.isoformat()
    run_id = "PQA-" + started_at.strftime("%Y%m%d%H%M%S")
    run_output = output / run_id
    run_output.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            expected_captures = 0
            for profile_name, profile in LAYOUT_GATE_PROFILES.items():
                profile_screens = selected_screens if profile_name in PROFILES else [
                    item for item in selected_screens if item[0] in EXTENDED_LAYOUT_SCREEN_KEYS
                ]
                expected_captures += len(profile_screens)
                context = browser.new_context(
                    viewport={"width": profile["width"], "height": profile["height"]},
                    is_mobile=profile["is_mobile"],
                    has_touch=profile["is_mobile"],
                    locale="es-ES",
                    timezone_id="Europe/Madrid",
                    service_workers="block",
                )
                context.route("**/*", _route_guard)
                _set_role_cookie(context, app_module, "client")
                page = context.new_page()
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("request", lambda request: provider_calls.append(request.url) if any(token in (urlparse(request.url).hostname or "") for token in BLOCKED_PROVIDER_HOSTS) else None)

                profile_dir = run_output / profile_name
                profile_dir.mkdir(parents=True, exist_ok=True)
                for key, route, audience in profile_screens:
                    context.clear_cookies()
                    if audience in {"client", "admin"}:
                        _set_role_cookie(context, app_module, audience)
                    response = page.goto(base_url + route, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(120)
                    page.evaluate("window.scrollTo(0, 0); document.scrollingElement.scrollTop = 0")
                    page.wait_for_timeout(40)
                    screenshot = profile_dir / f"{key}.png"
                    page.screenshot(path=str(screenshot), full_page=False)
                    inspection = _inspect(page, route.split("#", 1)[0], profile_name)
                    reference_file = reference_files.get(route.split("#", 1)[0], "")
                    inspection.update({
                        "key": key,
                        "http_status": response.status if response else 0,
                        "screenshot": str(screenshot),
                        "reference_file": reference_file,
                        "reference_match": _reference_similarity(screenshot, reference_file),
                    })
                    captures.append(inspection)

                context.clear_cookies()
                _set_role_cookie(context, app_module, "client")
                nav_zone = "client-desktop" if profile["width"] > 980 else "client-bottom"
                nav_contract = CLIENT_TOPBAR if profile["width"] > 980 else CLIENT_BOTTOM
                nav_shot = str(profile_dir / "home.png")
                page.goto(base_url + "/app", wait_until="domcontentloaded")
                for label, expected in nav_contract:
                    navigation_clicks.append(_exact_click(page, zone=nav_zone, label=label, expected_path=expected, screen="/app", viewport=profile_name, screenshot=nav_shot))

                if profile_name == "desktop_1366x768":
                    journeys.append(_public_golden_journey(page, base_url, qa_password))
                    journeys.append(_client_admin_separation_journey(page, base_url, app_module))
                    if args.scope == "full":
                        context.clear_cookies()
                        _set_role_cookie(context, app_module, "client")
                        journeys.append(_sports_golden_journey(page, base_url))
                        context.clear_cookies()
                        _set_role_cookie(context, app_module, "client")
                        journeys.append(_favorite_journey(page, base_url))
                        context.clear_cookies()
                        _set_role_cookie(context, app_module, "client")
                        journeys.append(_shark_golden_journey(page, base_url))
                        context.clear_cookies()
                        _set_role_cookie(context, app_module, "client")
                        journeys.append(_picks_golden_journey(page, base_url))
                        journeys.append(_account_golden_journey(page, base_url, qa_password))
                        journeys.append(_admin_golden_journey(page, base_url, qa_password))
                context.close()

            mobile_steps = []
            for click in navigation_clicks:
                if click.get("viewport") != "mobile_390x844":
                    continue
                expected = str(click.get("expected_path") or "")
                actual = str(click.get("actual_path") or "")
                mobile_steps.append({
                    "step": f"bottom_nav_{click.get('element')}",
                    "expected": expected,
                    "actual": actual,
                    "pass": bool(click.get("clicked") and click.get("hit_target") and actual.startswith(expected)),
                })
            journeys.append(_golden_journey("golden_mobile", mobile_steps))
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=3)

    home_capture = next((item for item in captures if item["key"] == "home" and item["viewport"] == "desktop_1366x768"), {})
    public_home = next((item for item in captures if item["key"] == "public_home" and item["viewport"] == "desktop_1366x768"), home_capture)
    mobile_capture = next((item for item in captures if item["key"] == "home" and item["viewport"] == "mobile_390x844"), {})
    technical_matches: list[str] = []
    mojibake_matches: list[str] = []
    for capture in captures:
        if str(capture.get("path") or "").startswith("/admin"):
            continue
        visible_text = str(capture.get("visible_text") or "")
        technical_matches.extend(match.group(0) for match in TECHNICAL_COPY_RE.finditer(visible_text))
        mojibake_matches.extend(match.group(0) for match in MOJIBAKE_RE.finditer(visible_text))
    technical_matches = list(dict.fromkeys(technical_matches))[:20]
    mojibake_matches = list(dict.fromkeys(mojibake_matches))[:20]
    sports_capture = public_home if public_home else home_capture
    match_capture = next((item for item in captures if item["key"] == "match" and item["viewport"] == "desktop_1366x768"), {})
    live_contract = sports_capture.get("live_contract") or {}
    broken_images = [f"{item.get('path')}: {image}" for item in captures for image in (item.get("broken_images") or [])]
    reference_match = home_capture.get("reference_match") or {}
    reference_classification = str(reference_match.get("classification") or "NOT_OBSERVED")
    shark_state = dict(home_capture.get("shark") or {})
    background_state = dict(home_capture.get("background") or {})
    if reference_classification in {"MAJOR_GAP", "REBUILD_REQUIRED", "NOT_OBSERVED"}:
        shark_state["classification"] = reference_classification
        background_state["classification"] = reference_classification
    shark_state["evidence"] = "; ".join(filter(None, [str(shark_state.get("evidence") or ""), str(reference_match.get("evidence") or "")]))
    background_state["evidence"] = "; ".join(filter(None, [str(background_state.get("evidence") or ""), str(reference_match.get("evidence") or "")]))
    client_admin_separation = next((item for item in journeys if item.get("journey") == "client_admin_separation"), {})
    admin_journey = next((item for item in journeys if item.get("journey") == "golden_admin"), {})
    sports_journey = next((item for item in journeys if item.get("journey") == "golden_sports_knowledge"), {})
    page_ready_samples = [int(item.get("page_ready_ms")) for item in captures if isinstance(item.get("page_ready_ms"), (int, float)) and int(item.get("page_ready_ms")) >= 0]
    performance_max = max(page_ready_samples) if page_ready_samples else None
    performance_status = "PASS" if performance_max is not None and performance_max <= 5000 else "FAIL" if performance_max is not None else "NOT_RUN"
    sports_priority = _sports_priority_regression(app_module)
    cross_surface_truth = _cross_surface_live_truth_evidence(captures)
    cross_surface_competition = _cross_surface_competition_identity_evidence(captures)
    temporal_context = _cross_surface_temporal_evidence(captures)
    temporal_context = _cross_surface_temporal_evidence(captures)
    layout_collisions = []
    for capture in captures:
        for collision in capture.get("layout_collisions") or []:
            layout_collisions.append({
                **collision,
                "screen": capture.get("path") or "/",
                "viewport": capture.get("viewport") or "unknown",
                "screenshot": capture.get("screenshot") or "",
                "evidence": (
                    f"{collision.get('type')}: {collision.get('element')}"
                    + (f" vs {collision.get('other')}" if collision.get("other") else "")
                    + f"; {collision.get('actual') or ''}"
                ),
            })
    composition_captures = []
    dead_space_flags = []
    empty_dashboard_flags = []
    for capture in captures:
        composition = capture.get("composition") or {}
        if not composition:
            continue
        composition_captures.append(composition)
        for flag in composition.get("dead_space_flags") or []:
            dead_space_flags.append({"screen": capture.get("path"), "viewport": capture.get("viewport"), "flag": flag})
        for flag in composition.get("empty_dashboard_flags") or []:
            empty_dashboard_flags.append({"screen": capture.get("path"), "viewport": capture.get("viewport"), "flag": flag})
    home_composition = home_capture.get("composition") or {}
    observation = {
        "run_id": run_id,
        "started_at_madrid": started,
        "production_sha": args.production_sha,
        "evidence_complete": bool(captures) and len(captures) == expected_captures and bool(journeys),
        "scope": args.scope,
        "next_expected_run": "Siguiente cambio, revision diaria critica o auditoria visual semanal, lo que ocurra primero.",
        "workers_executed": [
            "visual_experience_inspector",
            "digital_user_journey_tester",
            "sports_truth_qa",
            "mobile_qa",
            "admin_qa",
            "sports_knowledge_qa",
            "summary_truth_qa",
            "media_rights_qa",
        ],
        "navigation_clicks": navigation_clicks,
        "sports_truth": {
            "screen": sports_capture.get("path") or "/",
            "viewport": sports_capture.get("viewport") or "desktop_1366x768",
            "confirmed_live_count": live_contract.get("confirmed", 0),
            "displayed_live_count": live_contract.get("displayed", 0),
            "ft_rendered_live": live_contract.get("ft_rendered_live", 0),
            "cross_surface_live_truth": cross_surface_truth["pass"] if cross_surface_truth["observed"] else None,
            "cross_surface_live_mismatches": cross_surface_truth["mismatches"],
            "cross_surface_matches_compared": cross_surface_truth["matches_compared"],
            "important_match_priority": sports_priority["status"],
            "priority_evidence": sports_priority["evidence"],
            "screenshot": sports_capture.get("screenshot") or "",
            "evidence": "Contrato LIVE leído de la UI renderizada y comparado con el KPI visible.",
        },
        "competition_identity": {
            "screen": "sports surfaces",
            "viewport": "all",
            "pass": cross_surface_competition["pass"] if cross_surface_competition["observed"] else False,
            "matches_compared": cross_surface_competition["matches_compared"],
            "mismatches": cross_surface_competition["mismatches"],
            "evidence": "IDs canónicos leídos de las mismas cards renderizadas en todas las superficies deportivas.",
        },
        "layout_collisions": layout_collisions,
        "composition": {
            "observed": bool(composition_captures),
            "dead_space_flags": dead_space_flags,
            "empty_dashboard_flags": empty_dashboard_flags,
            "bordered_containers_max": max((int(item.get("bordered_containers") or 0) for item in composition_captures), default=0),
            "nested_card_depth_max": max((int(item.get("nested_card_depth") or 0) for item in composition_captures), default=0),
            "home_bordered_containers": int(home_composition.get("bordered_containers") or 0),
            "home_nested_card_depth": int(home_composition.get("nested_card_depth") or 0),
            "home_viewport_content_coverage": home_composition.get("viewport_content_coverage"),
            "home_sports_above_fold_ratio": home_composition.get("sports_above_fold_ratio"),
            "evidence": "Composición medida sobre el navegador renderizado: ocupación, paneles visibles, anidamiento y producto deportivo en el primer viewport.",
        },
        "layout": {
            "observed": bool(captures) and len(captures) == expected_captures,
            "captures": len(captures),
            "collision_types": sorted({str(item.get("type") or "") for item in layout_collisions if item.get("type")}),
            "collisions": len(layout_collisions),
            "mobile_360_captures": sum(1 for item in captures if item.get("viewport") == "mobile_360x800"),
            "mobile_360_collisions": sum(len(item.get("layout_collisions") or []) for item in captures if item.get("viewport") == "mobile_360x800"),
            "mobile_360_overflow": sum(1 for item in captures if item.get("viewport") == "mobile_360x800" and item.get("horizontal_overflow")),
        },
        "temporal_context": temporal_context,
        "layout": {
            "observed": bool(captures) and len(captures) == expected_captures,
            "captures": len(captures),
            "collision_types": sorted({str(item.get("type") or "") for item in layout_collisions if item.get("type")}),
            "collisions": len(layout_collisions),
            "mobile_360_captures": sum(1 for item in captures if item.get("viewport") == "mobile_360x800"),
            "mobile_360_collisions": sum(len(item.get("layout_collisions") or []) for item in captures if item.get("viewport") == "mobile_360x800"),
            "mobile_360_overflow": sum(1 for item in captures if item.get("viewport") == "mobile_360x800" and item.get("horizontal_overflow")),
        },
        "temporal_context": temporal_context,
        "sports_knowledge": {
            **(match_capture.get("sports_knowledge") or {}),
            "screen": match_capture.get("path") or "/match/m-1",
            "viewport": match_capture.get("viewport") or "desktop_1366x768",
            "screenshot": match_capture.get("screenshot") or "",
            "evidence": "Alineaciones, navegación de jugadores, resumen factual y derechos inspeccionados en el Match Center renderizado.",
        },
        "client_copy": {
            "screen": "client surfaces",
            "viewport": "all",
            "technical_matches": technical_matches,
            "evidence": "Copy visible inspeccionado en todas las superficies cliente capturadas.",
        },
        "text_quality": {
            "screen": "client surfaces",
            "viewport": "all",
            "mojibake_matches": mojibake_matches,
            "evidence": "Texto visible inspeccionado en el navegador real.",
        },
        "visual": {
            "shark": {**shark_state, "screen": "/app", "viewport": "desktop_1366x768", "screenshot": home_capture.get("screenshot") or ""},
            "background": {**background_state, "screen": "/app", "viewport": "desktop_1366x768", "screenshot": home_capture.get("screenshot") or ""},
        },
        "density": {
            "screen": "/app",
            "viewport": "desktop_1366x768",
            "first_viewport_product": home_capture.get("first_viewport_product"),
            "nested_panel_depth": home_capture.get("nested_panel_depth", 0),
            "nested_card_depth": home_composition.get("nested_card_depth", 0),
            "bordered_containers": home_composition.get("bordered_containers", 0),
            "dead_space_flags": home_composition.get("dead_space_flags") or [],
            "empty_dashboard_flags": empty_dashboard_flags,
            "sports_above_fold_ratio": home_composition.get("sports_above_fold_ratio", 0),
            "viewport_content_coverage": home_composition.get("viewport_content_coverage", 0),
            "screenshot": home_capture.get("screenshot") or "",
        },
        "mobile": {
            "screen": "/app",
            "viewport": "mobile_390x844",
            "overflow": mobile_capture.get("horizontal_overflow", False),
            "actual": mobile_capture.get("overflow_actual", ""),
            "screenshot": mobile_capture.get("screenshot") or "",
        },
        "security": {
            "client_admin_separation": "PASS" if client_admin_separation.get("pass") is True else "FAIL",
            "actual": client_admin_separation.get("actual"),
            "evidence": client_admin_separation.get("evidence") or client_admin_separation.get("error"),
            "viewport": "desktop_1366x768",
        },
        "performance": {
            "status": performance_status,
            "max_dom_ready_ms": performance_max,
            "sample_count": len(page_ready_samples),
            "evidence": f"Browser sample ligero: max_dom_ready_ms={performance_max}; samples={len(page_ready_samples)}.",
        },
        "quality_evidence": {
            "NAVIGATION": {"status": "PASS" if navigation_clicks and all(item.get("clicked") and item.get("hit_target") and item.get("page_ready") for item in navigation_clicks) else "FAIL"},
            "VISUAL": {
                "status": "WARNING"
                if str(shark_state.get("classification") or "").upper() in {"MATCH", "MINOR_GAP"}
                and str(background_state.get("classification") or "").upper() in {"MATCH", "MINOR_GAP"}
                and not layout_collisions
                and not dead_space_flags
                and not empty_dashboard_flags
                else "FAIL"
            },
            "SPORTS_TRUTH": {"status": "PASS" if int(live_contract.get("confirmed") or 0) == int(live_contract.get("displayed") or 0) and int(live_contract.get("ft_rendered_live") or 0) == 0 else "FAIL"},
            "MOBILE": {"status": "PASS" if not mobile_capture.get("horizontal_overflow", False) and not any(str(item.get("viewport") or "").startswith("mobile_") for item in layout_collisions) else "FAIL"},
            "ADMIN": {"status": "PASS" if admin_journey.get("pass") is True and not technical_matches and not mojibake_matches else "FAIL"},
            "SECURITY": {"status": "PASS" if client_admin_separation.get("pass") is True else "FAIL"},
            "PERFORMANCE": {"status": performance_status},
            "SPORTS_KNOWLEDGE": {"status": "PASS" if sports_journey.get("pass") is True else "FAIL"},
            "MEDIA_RIGHTS": {"status": "PASS" if int((match_capture.get("sports_knowledge") or {}).get("unsafe_media_visible") or 0) == 0 else "FAIL"},
            "SUMMARY_TRUTH": {"status": "PASS" if int((match_capture.get("sports_knowledge") or {}).get("summary_unsupported_claims") or 0) == 0 else "FAIL"},
            "DATA_QUALITY": {"status": "PASS" if not broken_images and not console_errors and not page_errors else "FAIL"},
        },
        "screenshots": [item.get("screenshot") for item in captures],
        "provider_calls": len(provider_calls),
        "journeys": journeys,
        "runtime": {
            "screen": "multiple",
            "viewport": "all",
            "js_errors": [*console_errors, *page_errors],
            "broken_images": broken_images,
            "evidence": "Consola, errores de pagina e imagenes inspeccionados durante el render real.",
        },
    }
    result = record_product_qa_run(
        observation,
        project_root=ROOT,
        trigger=args.trigger,
        evidence_origin=args.evidence_origin,
    )
    payload = {
        "contract": "NEMESIS-AUTONOMOUS-PRODUCT-QA-BROWSER-EVIDENCE-V1",
        "run": result,
        "captures": captures,
        "navigation_clicks": navigation_clicks,
        "journeys": journeys,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "provider_calls": provider_calls,
        "telegram_sent": 0,
        "stripe_actions": 0,
        "production_mutations": 0,
        "scope": args.scope,
    }
    result_path = run_output / "autonomous_product_qa_result.json"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": result.get("result"),
        "issues": result.get("issues_detected"),
        "captures": len(captures),
        "navigation_clicks": len(navigation_clicks),
        "journeys_pass": sum(1 for item in journeys if item.get("pass")),
        "journeys_total": len(journeys),
        "console_errors": len(console_errors),
        "page_errors": len(page_errors),
        "provider_calls": len(provider_calls),
        "output": str(result_path),
    }, ensure_ascii=False, indent=2))
    return 0 if result.get("result") == "PASS" and all(item.get("pass") for item in journeys) else 1


if __name__ == "__main__":
    raise SystemExit(main())
