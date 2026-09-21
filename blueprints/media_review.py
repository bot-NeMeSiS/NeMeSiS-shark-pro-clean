"""Media review sub-blueprint mounted explicitly by the existing admin composition factory."""
from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, session
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
        if request.method == 'POST' and not validate_csrf(session, request.form.get('csrf_token')):
            return jsonify({'ok': False, 'error': 'csrf_failed'}), 403

    @bp.get('/admin/highlights-review')
    def index():
        snapshot = review_snapshot(db_path)
        return render_template('admin_highlights_review.html', data={}, review=snapshot, review_error='')

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

    return bp
