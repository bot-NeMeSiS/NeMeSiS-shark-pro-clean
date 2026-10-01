"""Media review sub-blueprint mounted explicitly by the existing admin composition factory."""
from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for, flash
from engines.highlight_review_engine import ReviewError, decide_highlight, review_snapshot
from engines.security_engine import validate_csrf


def create_media_review_blueprint(db_path, is_admin_callback):
    bp = Blueprint('media_review', __name__)

    @bp.before_request
    def protect():
        try:
            admin = bool(is_admin_callback())
        except Exception:
            admin = False
        if not admin:
            return jsonify({'ok': False, 'error': 'admin_required'}), 403
        if request.method == 'POST':
            try:
                csrf_ok = validate_csrf(session, request.form.get('csrf_token'))
            except (TypeError, ValueError):
                # Malformed tokens must fail closed, not raise a server error.
                csrf_ok = False
            if not csrf_ok:
                return jsonify({'ok': False, 'error': 'csrf_failed'}), 403

    @bp.after_request
    def private_review(response):
        response.headers['Cache-Control'] = 'private, no-store'
        response.vary.add('Cookie')
        return response

    @bp.get('/api/admin/highlights/readiness')
    def readiness():
        from engines.highlight_read_model import read_highlights_readiness
        result = read_highlights_readiness(db_path)
        return jsonify(result), (200 if result['ok'] else 503)

    @bp.get('/admin/highlights-review')
    def index():
        snapshot = review_snapshot(db_path)
        from engines.postmatch_store import Store
        return render_template('admin_highlights_review.html', data={}, review=snapshot, review_error='', postmatch=Store(db_path).snapshot())

    @bp.post('/admin/highlights-review/<highlight_id>/decision')
    def decide(highlight_id):
        try:
            actor = str(session.get('user_id') or session.get('admin_id') or 'authenticated-admin-session')
            decide_highlight(db_path, highlight_id, request.form, actor=actor)
        except ReviewError as exc:
            return render_template('admin_highlights_review.html', data={}, review=review_snapshot(db_path), review_error=str(exc)), 409
        except Exception:
            return jsonify({'ok': False, 'error': 'review_storage_unavailable'}), 503
        return redirect('/admin/highlights-review', code=303)

    @bp.post('/admin/highlights-review/sync')
    def sync():
        from engines.sportsdb_highlights_engine import sync_sportsdb_highlights
        # One explicit request checks today and yesterday, never changes rights or sends Telegram.
        result = sync_sportsdb_highlights(db_path, days_back=1, limit=100, force=False)
        return jsonify(result), (200 if result.get('ok') else 503)

    @bp.app_template_global('match_editorial')
    def match_editorial(context, match):
        from engines.match_editorial_engine import build_editorial
        from engines.match_news_store import snapshot
        return build_editorial(context, snapshot(db_path, str(match.get('id') or '')))

    @bp.get('/admin/highlights-review/news')
    def news_index():
        from engines.match_news_store import snapshot
        model = snapshot(db_path, request.args.get('match_id', ''), admin=True)
        status = 503 if model['state'] == 'READ_UNAVAILABLE' else 404 if model['state'] == 'MATCH_NOT_FOUND' else 200
        return render_template('admin_match_news.html', data={}, news=model, review_error=''), status

    @bp.post('/admin/highlights-review/news/<match_id>/save')
    def news_save(match_id):
        from engines.match_news_store import save_draft, snapshot, NewsError
        import sqlite3
        actor = str(session.get('user_id') or session.get('admin_id') or 'authenticated-admin-session')
        try:
            save_draft(db_path, match_id, request.form, actor=actor)
        except NewsError as exc:
            return render_template('admin_match_news.html', data={}, news=snapshot(db_path, match_id, admin=True), review_error=str(exc)), 409
        except (sqlite3.Error, OSError):
            return jsonify(ok=False, error='news_storage_unavailable'), 503
        flash('Borrador guardado. Revisa la referencia antes de publicarla.', 'success')
        return redirect(url_for('.news_index', match_id=match_id), code=303)

    @bp.post('/admin/highlights-review/news/<match_id>/<int:news_id>/decision')
    def news_decision(match_id, news_id):
        from engines.match_news_store import decide, snapshot, NewsError
        import sqlite3
        actor = str(session.get('user_id') or session.get('admin_id') or 'authenticated-admin-session')
        try:
            state = decide(db_path, match_id, news_id, request.form, actor=actor)
        except NewsError as exc:
            return render_template('admin_match_news.html', data={}, news=snapshot(db_path, match_id, admin=True), review_error=str(exc)), 409
        except (sqlite3.Error, OSError):
            return jsonify(ok=False, error='news_storage_unavailable'), 503
        flash('Referencia publicada en la ficha.' if state == 'PUBLISHED' else 'Referencia retirada; el historial se conserva.', 'success')
        return redirect(url_for('.news_index', match_id=match_id), code=303)

    return bp
