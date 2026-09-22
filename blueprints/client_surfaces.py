"""Pure display helpers composed once, without replacing application routes."""
from flask import Blueprint
from engines.client_live_surface import live_surface


def create_client_surfaces_blueprint():
    bp = Blueprint('client_surfaces', __name__)

    @bp.app_context_processor
    def helpers():
        return {'client_live_surface':live_surface}

    return bp
