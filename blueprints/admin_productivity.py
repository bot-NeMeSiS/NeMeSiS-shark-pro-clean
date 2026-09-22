"""Presentation helpers on existing protected pages; no new routes or task writes."""
from flask import Blueprint, request
from engines.admin_operations_workbench import build_admin_workbench

PAGES = frozenset(('/admin/operations-center','/admin/operations','/admin/company-operations',
                   '/admin/centro-operaciones','/admin/sala-control'))


def create_admin_productivity_blueprint(is_admin):
    bp = Blueprint('admin_productivity',__name__)

    @bp.app_context_processor
    def workbench_helper():
        if request.path not in PAGES:
            return {}
        try:
            allowed = bool(is_admin())
        except Exception:
            allowed = False
        return {'admin_workbench':build_admin_workbench} if allowed else {}

    @bp.after_app_request
    def protect_operational_reading(response):
        if request.path in PAGES or request.path.startswith('/api/admin/operations-center/'):
            response.headers['Cache-Control']='private, no-store'
            response.vary.add('Cookie')
        return response

    return bp
