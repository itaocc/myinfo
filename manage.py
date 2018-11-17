import redis
from flask import Flask
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_session import Session

from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect


app = Flask(__name__)

# 配置
app.config.from_object(Config)
db = SQLAlchemy(app)
redis_store = redis.StrictRedis(host=Config.REDIS_HOST, port=Config.REDIS_PORT)

# csrf-token
CSRFProtect(app)    # 初始化csrf保护机制

Session(app)    # 初始化拓展session对象

# flask-scrip与数据库迁移管理
manager = Manager(app)  # 创建管理对象
Migrate(app, db)  # 创建迁移对象
manager.add_command('db', MigrateCommand)  # 迁移命令

@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    manager.run()
