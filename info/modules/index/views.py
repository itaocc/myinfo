from . import index_bp
from flask import render_template, current_app


@index_bp.route('/')
def index():
    """返回模板文件"""
    return render_template('news/index.html')


@index_bp.route('/favicon.ico')
def favicon():
    """返回网站图标"""
    return current_app.send_static_file('news/favicon.ico')  # send_static_file 是系统访问静态文件所调用的方法
