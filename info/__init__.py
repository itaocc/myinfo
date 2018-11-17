import redis
from flask import Flask
from flask_session import Session

from config import config_dict
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()   # 没有app对象时不初始化, 只是声明
redis_store = None


def create_app(config_name):
    """封装app创建的方法"""
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

    Session(app)  # 初始化拓展session对象

    return app

