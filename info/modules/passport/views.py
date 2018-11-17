from flask import request, abort, current_app, make_response, jsonify

from info import redis_store, constants
from utils.captcha.captcha import captcha
from . import passport_bp


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