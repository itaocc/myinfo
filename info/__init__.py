from logging.handlers import RotatingFileHandler

import redis, logging
from flask import Flask
from flask_session import Session
from flask_wtf.csrf import generate_csrf

from config import config_dict
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()   # 没有app对象时不初始化, 只是声明
redis_store = None  # 类型为StrictRedis


def setup_log(config_name):
    """配置日志"""
    config_class = config_dict[config_name]
    # 设置日志的记录等级
    logging.basicConfig(level=config_class.LOG_LEVEL)
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


def create_app(config_name):
    """封装app创建的方法"""
    setup_log(config_name)
    app = Flask(__name__)

    # 配置
    config_class = config_dict[config_name]
    app.config.from_object(config_class)
    # 创建数据库对象(懒加载思想)
    db.init_app(app)  # db没有对象时为空, 不为空时调用此句方法

    global redis_store
    redis_store = redis.StrictRedis(host=config_class.REDIS_HOST, port=config_class.REDIS_PORT)

    # csrf-token
    csrf = CSRFProtect(app)  # 初始化csrf保护机制

    # 使用钩子函数统一设置cookie值
    @app.after_request
    def set_csrftoken(response):
        # 1.生成csrf_token随机值
        csrf_token = generate_csrf()
        # 2.借助response对象设置csrf_token值到cookie中
        response.set_cookie("csrf_token", csrf_token)
        # 3.返回响应对象
        return response

    Session(app)  # 初始化拓展session对象

    # 首页蓝图注册
    from info.modules.index import index_bp
    app.register_blueprint(index_bp)

    # 登录, 注册模块蓝图注册
    from info.modules.passport import passport_bp
    app.register_blueprint(passport_bp)

    return app

