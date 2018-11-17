from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from info import create_app, db, models
from pymysql import install_as_MySQLdb
install_as_MySQLdb()


app = create_app("development")

# flask-scrip与数据库迁移管理
manager = Manager(app)  # 创建管理对象
Migrate(app, db)  # 创建迁移对象
manager.add_command('db', MigrateCommand)  # 迁移命令

if __name__ == '__main__':
    manager.run()
