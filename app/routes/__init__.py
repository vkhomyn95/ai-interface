from flask import Blueprint
from .api import apis
from .base import bases

apis_bp = Blueprint("apis", __name__, url_prefix="/api")
apis_bp.register_blueprint(apis)

bases_bp = Blueprint("bases", __name__, url_prefix="/")
bases_bp.register_blueprint(bases)
