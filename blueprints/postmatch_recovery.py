"""Post-match workers: header-authenticated Cron and admin/CSRF-only controls."""
from __future__ import annotations
import hmac
import os
import sqlite3
from flask import Blueprint, jsonify, redirect, render_template, request, session
from engines.postmatch_store import Store
from engines.postmatch_recovery import tick
from engines.security_engine import validate_csrf


def create_postmatch_blueprint(db_path, is_admin_callback, priority=None):
    bp = Blueprint('postmatch_recovery', __name__)

    @bp.before_request
    def protect():
        if request.path == '/api/automation/postmatch/tick':
            expected = (os.getenv('AUTOMATION_SECRET') or '').strip()
            supplied = request.headers.get('X-Automation-Secret') or ''
            if not expected or not hmac.compare_digest(expected.encode(), supplied.encode()):
                return jsonify(ok=False, result='FORBIDDEN'), 403
            return None
        try:
            admin = bool(is_admin_callback())
            csrf = request.method != 'POST' or validate_csrf(session, request.form.get('csrf_token'))
        except Exception:
            admin = csrf = False
        if not admin or not csrf:
            return jsonify(ok=False, result='FORBIDDEN'), 403

    @bp.after_request
    def private(response):
        response.headers['Cache-Control'] = 'private, no-store'
        response.vary.add('Cookie')
        return response

    @bp.post('/api/automation/postmatch/tick')
    def cron():
        options = {'priority':priority} if priority is not None else {}
        result = tick(db_path, dry_run=request.args.get('dry_run') == '1',**options)
        return jsonify(result), (200 if result.get('ok') else 503)

    @bp.get('/api/admin/postmatch/status')
    def status():
        result = Store(db_path).snapshot()
        return jsonify(result), (503 if result['state'] == 'READ_UNAVAILABLE' else 200)

    @bp.post('/admin/highlights-review/workers/settings')
    def settings():
        try:
            Store(db_path).configure(enabled=request.form.get('enabled') == '1',
                sources=request.form.getlist('sources'), daily_limit=request.form.get('daily_limit', '60'),
                actor=session.get('user_id') or 'admin-session', confirmed=request.form.get('confirmed') == '1')
        except ValueError as exc:
            return jsonify(ok=False, result='INVALID_CONFIGURATION', message=str(exc)), 400
        except (sqlite3.Error, OSError):
            return jsonify(ok=False, result='STORAGE_UNAVAILABLE'), 503
        return redirect('/admin/highlights-review#postmatch-workers', code=303)

    @bp.post('/admin/highlights-review/workers/run')
    def run():
        result = tick(db_path,**({'priority':priority} if priority is not None else {}))
        if request.form.get('return_to_panel') == '1':
            from engines.postmatch_delivery import safe_run_result
            session['postmatch_last_result'] = safe_run_result(result)
            return redirect('/admin/highlights-review/workers/result', code=303)
        return jsonify(result), (200 if result.get('ok') else 503)

    @bp.get('/admin/highlights-review/workers/result')
    def run_result():
        from engines.postmatch_delivery import present_run_result
        # A refresh repeats a GET, not the paid query. Authentication still applies.
        result = session.get('postmatch_last_result')
        presentation = present_run_result(result, Store(db_path))
        return render_template('admin_postmatch_result.html', data={}, delivery=presentation), (503 if result and not result.get('ok') else 200)

    @bp.post('/admin/highlights-review/workers/<int:job_id>/retry')
    def retry(job_id):
        try:
            Store(db_path).requeue(job_id, session.get('user_id') or 'admin-session')
        except ValueError as exc:
            return jsonify(ok=False, result='RETRY_REJECTED', message=str(exc)), 409
        except (sqlite3.Error, OSError):
            return jsonify(ok=False, result='STORAGE_UNAVAILABLE'), 503
        return redirect('/admin/highlights-review#postmatch-workers', code=303)

    @bp.post('/admin/highlights-review/workers/statistics/<int:observation_id>/select')
    def select_statistics(observation_id):
        from engines.postmatch_recovery import select_observation
        if request.form.get('confirmed') != '1':
            return jsonify(ok=False, result='REVIEW_CONFIRMATION_REQUIRED'), 400
        try:
            select_observation(db_path, observation_id, actor=session.get('user_id') or 'admin-session',
                expected_identity=request.form.get('identity'), expected_revision=request.form.get('selection_revision'))
        except ValueError as exc:
            return jsonify(ok=False, result='STALE_OR_INVALID_REVIEW', message=str(exc)), 409
        except (sqlite3.Error, OSError):
            return jsonify(ok=False, result='STORAGE_UNAVAILABLE'), 503
        return redirect('/admin/highlights-review#postmatch-workers', code=303)

    return bp
