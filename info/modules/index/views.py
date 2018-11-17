from . import index_bp


@index_bp.route('/')
def index():

    return 'index'
