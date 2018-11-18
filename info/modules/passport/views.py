import random
import re, json

from flask import request, abort, current_app, make_response, jsonify

from info import redis_store, constants
from lib.yuntongxun.sms import CCP
from info.models import User
from utils.captcha.captcha import captcha
from utils.response_code import RET
from . import passport_bp


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
@passport_bp.route('/sms_code')
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