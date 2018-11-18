from info.models import User
from utils.response_code import RET
from . import index_bp
from flask import render_template, current_app, session, jsonify


@index_bp.route('/')
def index():
    """返回模板文件"""
    # 获取当前登录用户的id
    user_id = session.get("user_id")
    user = None
    if user_id:
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询用户异常")
    data = {
        "user_info": user.to_dict() if user else None
    }
    return render_template('news/index.html', data=data)


@index_bp.route('/favicon.ico')
def favicon():
    """返回网站图标"""
    return current_app.send_static_file('news/favicon.ico')  # send_static_file 是系统访问静态文件所调用的方法
