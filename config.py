import redis, logging


class Config(object):
    """工程配置信息"""
    DEBUG = True

    # 数据库配置信息
    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/info"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # redis数据库配置
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_NUM = 7 # 选择第8个数据库进行存储

    # session设置, 将flask中的session存储位置从内存调整到redis存储
    SECRET_KEY = 'ASAERD12WQIDFNDSER43VXSSQ1323FSDCX'
    SESSION_TYPE = "redis"  # 指定 session 保存到 redis 中
    SESSION_USE_SIGNER = True  # 让 cookie 中的 session_id 被加密签名处理
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)  # 使用 redis 的实例
    PERMANENT_SESSION_LIFETIME = 86400  # session 的有效期，单位是秒

    # 默认日志等级
    LOG_LEVEL = logging.DEBUG

class DevelopmentConfig(Config):
    """开发环境的项目配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境的项目配置"""
    LOG_LEVEL = logging.WARNING


# 定义配置字典, 提供接口给外界使用
config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}



