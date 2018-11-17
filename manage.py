from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from info import create_app, db

app = create_app("development")

# flask-scrip与数据库迁移管理
manager = Manager(app)  # 创建管理对象
Migrate(app, db)  # 创建迁移对象
manager.add_command('db', MigrateCommand)  # 迁移命令


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    manager.run()
