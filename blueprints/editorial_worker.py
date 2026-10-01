"""Nested in media_review: inherits ADMIN, CSRF and private response protections."""
from __future__ import annotations
from datetime import datetime
import sqlite3
from flask import Blueprint, flash, jsonify, redirect, request, session
from engines import editorial_worker as worker
from engines.match_news_store import NewsError


def create_editorial_blueprint(db_path):
    bp = Blueprint('editorial_worker', __name__)

    @bp.app_template_global('editorial_status')
    def editorial_status():
        # Invoked only by the admin partial; no fetch, initialization or writes.
        return worker.state(db_path)

    @bp.app_template_filter('editorial_madrid')
    def editorial_madrid(value):
        from zoneinfo import ZoneInfo
        return datetime.fromtimestamp(float(value),ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y %H:%M') if value else '—'

    def actor():
        return str(session.get('user_id') or session.get('admin_id') or 'authenticated-admin-session')

    def execute(fn):
        try: fn()
        except NewsError as exc: flash(str(exc),'error')
        except (sqlite3.Error,OSError):
            flash('No se pudo guardar. La configuración no se da por actualizada.','error')
        return redirect('/admin/highlights-review/news#editorial-worker',code=303)

    @bp.get('/api/admin/editorial/status')
    def status():
        snap=worker.state(db_path)
        return jsonify(snap), (503 if snap['state']=='READ_UNAVAILABLE' else 200)

    @bp.post('/admin/highlights-review/editor/sources')
    def add_source():
        def run():
            worker.add_source(db_path,request.form,actor=actor())
            flash('Fuente registrada. El editor no se activa hasta guardar su configuración.','success')
        return execute(run)

    @bp.post('/admin/highlights-review/editor/configure')
    def configure():
        def run():
            worker.configure(db_path,request.form,actor=actor())
            flash('Configuración editorial guardada.','success')
        return execute(run)

    @bp.post('/admin/highlights-review/editor/sources/<int:source_id>/action')
    def source_action(source_id):
        def run():
            worker.source_action(db_path,source_id,request.form,actor=actor())
            flash('Acción registrada; no se ha borrado el historial.','success')
        return execute(run)

    @bp.post('/admin/highlights-review/editor/run')
    def run_now():
        result=worker.tick(db_path)
        labels={'PAUSED':'El editor está en pausa. No se han hecho consultas.',
                'RUNNING':'Ya hay una revisión en curso; no se duplica.',
                'IDLE':'No hay fuentes pendientes de revisión.',
                'DAILY_BUDGET':'Se alcanzó el límite diario. No se hacen más consultas.',
                'REFERENCES_UPDATED':f"Revisión terminada: {result.get('published',0)} referencias publicadas y {result.get('drafts',0)} borradores.",
                'NO_NEW_REFERENCES':'Fuente revisada; no hay referencias nuevas inequívocas.',
                'TIME_BUDGET':'Revisión aplazada por el límite de tiempo.',
                'STALE_EXECUTION':'La configuración cambió durante la consulta; no se publicó el resultado.'}
        flash(labels.get(result['result'],'La revisión requiere atención. Consulta el estado de la fuente.'), 'success' if result.get('ok') else 'error')
        return redirect('/admin/highlights-review/news#editorial-worker',code=303)

    return bp
