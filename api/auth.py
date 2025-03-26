#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API认证模块

提供多种认证方式:
1. API密钥验证：支持多密钥和HMAC签名验证
2. IP白名单：限制只允许特定IP地址访问API
3. JWT令牌验证：使用JWT进行身份认证，支持角色和权限控制
4. 速率限制：防止API被滥用
"""

import time
import hashlib
import hmac
import base64
import ipaddress
import json
import functools
import uuid
from datetime import datetime, timedelta

import jwt
import redis
from flask import request, jsonify, current_app, g
from utils.logging import get_logger

logger = get_logger(__name__)


def _get_client_ip():
    """
    获取客户端真实IP地址
    
    Returns:
        str: 客户端IP地址
    """
    # 获取X-Forwarded-For头，处理代理情况
    if request.headers.get('X-Forwarded-For'):
        # 获取最左边的IP（最初的客户端）
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        client_ip = request.remote_addr
    
    return client_ip


def check_ip_whitelist(client_ip):
    """
    检查IP是否在白名单中
    
    Args:
        client_ip (str): 客户端IP地址
        
    Returns:
        bool: IP是否在白名单中
    """
    # 如果白名单功能未启用，直接返回True
    if not current_app.config.get('IP_WHITELIST_ENABLED', False):
        return True
        
    ip_whitelist = current_app.config.get('IP_WHITELIST', [])
    
    # 如果白名单为空，也返回True
    if not ip_whitelist:
        return True
    
    # 转换为IP地址对象进行比较
    try:
        client = ipaddress.ip_address(client_ip)
        
        # 检查IP是否在白名单中
        for allowed_ip in ip_whitelist:
            # 检查是否为CIDR格式
            if '/' in allowed_ip:
                if client in ipaddress.ip_network(allowed_ip, strict=False):
                    return True
            # 检查是否为单个IP
            elif client == ipaddress.ip_address(allowed_ip):
                return True
                
        # IP不在白名单中
        logger.warning(f"IP白名单验证失败: {client_ip} 不在允许列表中")
        return False
    except ValueError:
        logger.error(f"IP地址格式错误: {client_ip}")
        return False


def verify_api_key(api_key):
    """
    验证API密钥是否有效
    
    Args:
        api_key (str): API密钥
        
    Returns:
        bool: API密钥是否有效
    """
    # 检查API密钥是否空
    if not api_key:
        return False
    
    # 获取配置的API密钥
    configured_api_key = current_app.config.get('API_KEY')
    api_keys = current_app.config.get('API_KEYS', [])
    
    # 检查是否是HMAC签名格式
    if ':' in api_key:
        key_id, signature = api_key.split(':', 1)
        
        # 检查key_id是否在允许的API密钥列表中
        if key_id not in api_keys:
            logger.warning(f"未知的API密钥ID: {key_id}")
            return False
            
        # 获取时间戳和消息
        timestamp = request.headers.get('X-Timestamp')
        if not timestamp:
            logger.warning("缺少时间戳头")
            return False
            
        # 检查时间戳是否过期（30秒内有效）
        try:
            ts = float(timestamp)
            if abs(time.time() - ts) > 30:
                logger.warning(f"时间戳过期: {timestamp}")
                return False
        except ValueError:
            logger.warning(f"无效的时间戳格式: {timestamp}")
            return False
            
        # 构造待签名消息（URL+方法+时间戳）
        method = request.method
        path = request.path
        message = f"{method}:{path}:{timestamp}"
        
        # 使用HMAC验证签名
        hmac_secret = current_app.config.get('HMAC_SECRET', '')
        expected_signature = hmac.new(
            hmac_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        expected_signature = base64.b64encode(expected_signature).decode()
        
        # 比较签名
        if signature != expected_signature:
            logger.warning(f"签名验证失败: {signature} != {expected_signature}")
            return False
            
        # 签名验证通过
        g.auth_method = 'hmac'
        g.key_id = key_id
        return True
    
    # 检查直接密钥
    if api_key == configured_api_key or api_key in api_keys:
        g.auth_method = 'api_key'
        return True
        
    # API密钥无效
    logger.warning(f"无效的API密钥: {api_key[:5]}...")
    return False


def check_rate_limit():
    """
    检查请求速率限制，基于IP地址进行限制
    
    Returns:
        bool: 是否超过速率限制
    """
    # 如果速率限制功能未启用，直接返回True
    if not current_app.config.get('RATE_LIMIT_ENABLED', True):
        return True
        
    # 获取速率限制配置
    rate_limit = current_app.config.get('RATE_LIMIT', 100)  # 默认100个请求
    period = current_app.config.get('RATE_LIMIT_PERIOD', 60)  # 默认60秒
    
    # 获取客户端IP
    client_ip = _get_client_ip()
    
    # 创建Redis键
    redis_key = f"rate_limit:{client_ip}:{int(time.time() / period)}"
    
    try:
        # 连接到Redis
        redis_config = current_app.config.get('REDIS_CONFIG', {})
        redis_client = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password', None),
            decode_responses=True
        )
        
        # 获取当前计数
        current_count = redis_client.get(redis_key)
        if current_count is None:
            # 第一次请求，设置计数为1，并设置过期时间
            redis_client.set(redis_key, 1, ex=period)
            return True
            
        # 转换为整数
        current_count = int(current_count)
        
        # 检查是否超过限制
        if current_count >= rate_limit:
            logger.warning(f"速率限制超过: {client_ip} - {current_count}/{rate_limit}")
            return False
            
        # 递增计数
        redis_client.incr(redis_key)
        return True
    except Exception as e:
        # Redis连接失败时，默认放行
        logger.error(f"速率限制检查失败: {str(e)}")
        return True


def generate_jwt(user_id, role='user', expires_in=3600):
    """
    生成JWT令牌
    
    Args:
        user_id (str): 用户ID
        role (str): 用户角色
        expires_in (int): 过期时间(秒)
        
    Returns:
        str: JWT令牌
    """
    try:
        # 生成过期时间
        exp = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # 构造JWT载荷
        payload = {
            'sub': user_id,
            'role': role,
            'iat': datetime.utcnow(),
            'exp': exp,
            'jti': str(uuid.uuid4())  # JWT ID，防止重放攻击
        }
        
        # 使用密钥签名JWT
        jwt_secret = current_app.config.get('JWT_SECRET', '')
        token = jwt.encode(payload, jwt_secret, algorithm='HS256')
        
        # 根据不同版本的PyJWT返回结果
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token
    except Exception as e:
        logger.error(f"JWT生成失败: {str(e)}")
        return None


def verify_jwt(token):
    """
    验证JWT令牌
    
    Args:
        token (str): JWT令牌
        
    Returns:
        dict: JWT载荷，如果无效则返回None
    """
    try:
        # 使用密钥验证JWT
        jwt_secret = current_app.config.get('JWT_SECRET', '')
        payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        
        # 验证成功后，将用户信息存储到g对象中
        g.user_id = payload.get('sub')
        g.user_role = payload.get('role')
        g.auth_method = 'jwt'
        
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"JWT已过期: {token[:10]}...")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"无效的JWT: {token[:10]}... - {str(e)}")
        return None
    except Exception as e:
        logger.error(f"JWT验证失败: {str(e)}")
        return None


def require_auth(f):
    """
    API认证装饰器，要求请求包含有效的认证信息
    
    具体验证流程：
    1. 首先验证JWT令牌（如启用）
    2. 然后验证IP白名单（如启用）
    3. 最后验证API密钥
    
    任一验证通过即可访问API
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # 检查请求权限
        auth_success = False
        
        # 初始化认证方法
        g.auth_method = None
        
        # 获取客户端IP
        client_ip = _get_client_ip()
        g.client_ip = client_ip
        
        # 检查速率限制
        if not check_rate_limit():
            return jsonify({
                'success': False,
                'error': 'Rate Limit Exceeded',
                'message': '请求频率超过限制'
            }), 429
        
        # 1. 首先尝试JWT认证（如果启用）
        if current_app.config.get('JWT_AUTH_ENABLED', False):
            # 从Authorization头获取Bearer令牌
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # 去掉'Bearer '前缀
                payload = verify_jwt(token)
                if payload:
                    auth_success = True
        
        # 2. 然后检查IP白名单（如果启用且JWT未通过）
        if not auth_success:
            if not check_ip_whitelist(client_ip):
                logger.warning(f"IP白名单验证失败: {client_ip}")
                return jsonify({
                    'success': False,
                    'error': 'Forbidden',
                    'message': '您的IP地址没有访问权限'
                }), 403
        
        # 3. 最后检查API密钥（如果JWT未通过）
        if not auth_success:
            # 从请求头或URL参数获取API密钥
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            
            if not api_key:
                logger.warning(f"缺少API密钥 | IP: {client_ip}")
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': '缺少API密钥'
                }), 401
            
            # 验证API密钥
            if not verify_api_key(api_key):
                logger.warning(f"无效的API密钥 | IP: {client_ip}")
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'API密钥无效'
                }), 401
            
            auth_success = True
        
        # 记录认证方法和IP
        logger.debug(f"认证成功: 方法={g.auth_method} | IP={client_ip}")
        
        # 调用被装饰的函数
        return f(*args, **kwargs)
    
    return decorated 