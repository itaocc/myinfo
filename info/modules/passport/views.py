import random
import re, json

from datetime import datetime
from flask import request, abort, current_app, make_response, jsonify, session

from info import redis_store, constants, db
from lib.yuntongxun.sms import CCP
from info.models import User
from utils.captcha.captcha import captcha
from utils.response_code import RET
from . import passport_bp


@passport_bp.route('/login', methods=["POST"])
def login():
    """登录接口"""
    """
       1.获取参数
           1.1 mobile手机号码，password未加密密码
       2.校验参数
           2.1 非空判断
           2.2 手机号码正则校验
       3.逻辑处理
           3.0 查询用户是否存在
           3.1 验证密码是否一致
           3.2 不一致： 提示密码填写错误
           3.3 一致：记录用户登录信息
       4.返回值
           登录成功
       """
    # 1.1 mobile手机号码，password未加密密码
    param_dict = request.json
    mobile = param_dict.get("mobile")
    password = param_dict.get("password")
    # 2.1 非空判断
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 手机号码正则校验
    if not re.match('1[3578][0-9]{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机格式错误")

    # 3.0 查询用户是否存在
    try:
        user = User.query.filter(User.mobile == mobile).first()  # filter查询的第一个
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
    # 用户不存在
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    # 3.1 验证密码是否一致
    if not user.check_passowrd(password):
        # 3.2 不一致： 提示密码填写错误
        return jsonify(errno=RET.DATAERR, errmsg="密码填写错误")

    # 3.3 一致：记录用户登录信息
    session["user_id"] = user.id
    session["nick_name"] = user.mobile
    session['mobile'] = user.mobile

    # 更新用户最后一次登录时间
    user.last_login = datetime.now()
    # 修改了用户对象属性，要想更新到数据库必须commit
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()

    # 4.登录成功
    return jsonify(errno=RET.OK, errmsg="登录成功")


# 127.0.0.1:5000/passport/register
@passport_bp.route('/register', methods=['POST'])
def register():
    """用户注册接口"""
    """
    1.接收参数
        1.1 mobile手机号码, password密码, sms_code手机验证码
    2.参数校验
        2.1 非空判断
        2.2 手机号码正则校验
    3.逻辑处理
        3.1 根据sms_code_手机号码key去redis中取短信验证码的值
            3.1.1 有值: 执行删除操作(避免重复验证)
            3.1.2 没有值: 短信验证码过期
        3.2 比较用户填写的短信验证码和redis取出的值
        3.3 不一致： 提示验证码错误
        3.4 一致： 使用User模型创建用户对象并且赋值
        3.5 一般需求: 第一注册成功后应该登录, 记录session
    4.返回响应
     注册成功
    """
    # 1.1 mobile手机号码, password密码, sms_code手机验证码
    param_dict = request.json
    mobile = param_dict.get("mobile")
    smscode = param_dict.get("smscode")
    password = param_dict.get("password")

    # 2.1 非空判断
    if not all([mobile, smscode, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 手机号码正则校验
    if not re.match('1[3578][0-9]{9}', mobile):
        current_app.logger.error("手机号码格式有误")
        return jsonify(errno=RET.PARAMERR, errmsg="手机号码格式错误")

    # 3.1 根据sms_code_手机号码key去redis中取短信验证码的值
    try:
        real_smscode = redis_store.get("SMS_CODE_%s" % mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询真实短信验证码有误")
    # 3.1.1 有值: 执行删除操作(避免重复验证)
    if real_smscode:
        redis_store.delete("SMS_CODE_%s" % mobile)
    # 3.1.2 没有值: 短信验证码过期
    else:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码过期")

    # 3.2 比较用户填写的短信验证码和redis取出的值
    if real_smscode != smscode:
        # 3.3 不一致： 提示验证码错误
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码填写错误")
    # 3.4 一致： 使用User模型创建用户对象并且赋值
    user = User()
    # 用户参数赋值
    user.nick_name = mobile
    user.mobile = mobile
    user.last_login = datetime.now()
    user.password = password

    # 3.5 一般需求: 第一注册成功后应该登录, 记录session
    # 将用户对象存储到session中
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()   # 有异常,数据库回滚到存储之前的状态, 本次不存储

    session["user_id"] = user.id
    session["nick_name"] = user.mobile
    session["mobile"] = user.mobile

    # 4.返回注册成功
    return jsonify(errno=RET.OK, errmsg="注册成功")


# 127.0.0.1:5000/passport/image_code?code_id=uuid编号  (GET)
@passport_bp.route('/image_code')
def get_image_code():
    """获取图片验证码(GET)"""
    """
    1.获取参数
        1.1 获取code_id的唯一编号UUID
    2.参数校验
        2.1 判断code_id是否有值
    3.逻辑处理
        3.1 生成验证码图片和图片上的真实值
        3.2 以code_id作为key将验证码真实值存入redis
    4.返回值
        4.1 返回图片给前端
    """
    # 1.1 获取code_id的唯一编号UUID
    code_id = request.args.get('code_id')
    # 2.1 判断code_id是否有值
    if  not code_id:
        abort(404)  # code_id不存在抛出404异常

    # 3.1 生成验证码图片和图片上的真实值
    image_name, real_image_code, image_data = captcha.generate_captcha()
    try:
        # 3.2 以code_id作为key将验证码真实值存入redis
        redis_store.setex("imageCodeId_%s" % code_id, constants.IMAGE_CODE_REDIS_EXPIRES, real_image_code)
    except Exception as e:
        current_app.logger.error(e)
        abort(500)  # 保存到redis时异常抛出500

    # 4.1 返回图片给前端
    response = make_response(image_data)
    response.headers["Content-Type"] = "image/JPEG"  # 设置响应数据类型, Content-Type是返回值类型, 使数据可以兼容所有浏览器格式
    return response


# 127.0.0.1:5000/passport/sms_code
@passport_bp.route('/sms_code', methods=['POST'])
def send_sms_code():
    """点击发送短信验证码后端接口"""
    """
   1.获取参数
       1.1 手机号mobile, 用户填写的验证码值image_code, image_code_id的唯一编码uuid
   2.参数校验
       2.1 非空判断
       2.2 判断手机格式是否正确
   3.逻辑处理
       3.1 根据用户请求的uuid取redis存储的验证码真实值
           3.1.1 有值: 从redis数据库中删除真实值(防止多次验证)
           3.1.2 无值: 图片验证码值过期
       3.2 用户填写的image_code和真实值比较是否一致
           TODO:先查询当前手机号是否注册, 没有注册才发送短信验证码; 反之不需注册
           不一致: 提示图形验证码填写错误
       3.3 将生成的6位短信验证码存储到redis中
   4.返回值    
       4.1 返回图片给前端
   """
    # param_dict = request.json
    param_dict = json.loads(request.data)
    # 手机号码
    mobile = param_dict.get("mobile")
    # 用户填写的图片验证值
    image_code = param_dict.get("image_code")
    # uuid编号
    image_code_id = param_dict.get("image_code_id")
    print(mobile)

    # 2.1 非空判断
    if not all([mobile, image_code, image_code_id]):
        current_app.logger.error("参数不足")
        # 返回json格式的错误信息
        return jsonify({"errno": RET.PARAMERR, "errmsg": "参数不足"})
    # 2.2 手机号码格式正则判断
    if not re.match('1[3578][0-9]{9}', mobile):
        # 手机号码格式有问题
        current_app.logger.error("手机号码格式错误")
        return jsonify(errno=RET.PARAMERR, errmsg="手机号码格式错误")

    real_image_code = None
    try:
        # 3.1 image_code_id编号去redis数据库取出图片验证码的真实值
        real_image_code = redis_store.get("imageCodeId_%s" % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询图片验证码真实值异常")

    # 3.1.1 有值： 从redis数据库删除真实值（防止拿着相同的值多次验证）
    if real_image_code:
        redis_store.delete("imageCodeId_%s" % image_code_id)
    # 3.1.2 没有值：图片验证码值在redis中过期
    else:
        return jsonify(errno=RET.NODATA, errmsg="图片验证码值在redis中过期")

    # 3.2 比较用户填写的图片验证码值和真实的验证码值是否一致
    # 细节1：全部转成小写
    # 细节2：设置redis数据decode操作
    if real_image_code.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="图片验证码填写错误")

    """
        TODO: 手机号码有了（用户是否已经注册的判断，用户体验最好），
                根据手机号码去查询用户是否有注册，有注册，不需要再注册，没有注册才去发送短信验证码
    """
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户数据异常")

    # 用户存在
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg="用户已经注册")

    # 一致：填写正确，生成6位的短信验证码值，发送短信验证码
    # 生成6位的短信验证码值
    sms_code = random.randint(0, 999999)
    sms_code = "%06d" % sms_code
    # sms_code = 123456
    print(sms_code)
    # try:
    #     ccp = CCP()
    #     result = ccp.send_template_sms("18520340803", [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], 1)
    # except Exception as e:
    #     current_app.logger.error(e)
    #     return jsonify(errno=RET.THIRDERR, errmsg="云通讯发送短信验证码失败")
    # if result != 0:
    #     return jsonify(errno=RET.THIRDERR, errmsg="云通讯发送短信验证码失败")

    # 3.3 将生成6位的短信验证码值 存储到redis数据库
    try:
        redis_store.setex("SMS_CODE_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, 123456)
        print(redis_store.get(mobile))
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存短信验证码到数据库异常")

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="发送短信验证码成功")

