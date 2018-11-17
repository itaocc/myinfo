from flask import Blueprint

passport_bp  = Blueprint('passport', __name__, url_prefix='/passport')   # 指定动态url前缀

from . import views