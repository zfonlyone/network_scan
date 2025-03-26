#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API服务主模块
"""

import logging
import time
import os
import uuid
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from api.auth import require_auth, generate_jwt
from api.routes import api_bp
from utils.logging import get_logger

logger = get_logger(__name__)


def create_app(config=None):
    """
    创建Flask应用
    
    Args:
        config: 配置字典
        
    Returns:
        Flask: Flask应用实例
    """
    app = Flask(__name__)
    
    # 配置
    if config is None:
        config = {}
    
    # 修复代理头，确保获取正确的客户端IP
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # 基本配置
    app.config['API_KEY'] = config.get('api_key', os.environ.get('API_KEY', 'your-api-key'))
    app.config['PROXY_DB_CONFIG'] = config.get('database', {})
    app.config['REDIS_CONFIG'] = config.get('redis', {})
    
    # API密钥配置
    app.config['API_KEYS'] = config.get('api_keys', [])
    app.config['HMAC_SECRET'] = config.get('hmac_secret', os.environ.get('HMAC_SECRET', ''))
    
    # IP白名单配置
    app.config['IP_WHITELIST_ENABLED'] = config.get('ip_whitelist_enabled', False)
    app.config['IP_WHITELIST'] = config.get('ip_whitelist', [])
    
    # 速率限制配置
    app.config['RATE_LIMIT_ENABLED'] = config.get('rate_limit_enabled', True)
    app.config['RATE_LIMIT'] = config.get('rate_limit', 100)
    app.config['RATE_LIMIT_PERIOD'] = config.get('rate_limit_period', 60)
    
    # JWT认证配置
    app.config['JWT_AUTH_ENABLED'] = config.get('jwt_auth_enabled', False)
    app.config['JWT_SECRET'] = config.get('jwt_secret', os.environ.get('JWT_SECRET', uuid.uuid4().hex))
    app.config['JWT_EXPIRE_SECONDS'] = config.get('jwt_expire_seconds', 3600)  # 默认1小时
    
    # 添加请求处理中间件
    @app.before_request
    def before_request():
        """请求前处理"""
        g.start_time = time.time()
        
        # 记录请求信息
        client_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        logger.debug(f"收到请求: {request.method} {request.path} | IP: {client_ip} | UA: {user_agent}")
        
    @app.after_request
    def after_request(response):
        """请求后处理"""
        diff = time.time() - g.get('start_time', time.time())
        logger.debug(f"请求处理耗时: {diff:.3f}秒 - {request.method} {request.path} - 状态码: {response.status_code}")
        
        # 添加安全头
        response.headers.add('X-Content-Type-Options', 'nosniff')
        response.headers.add('X-Frame-Options', 'DENY')
        response.headers.add('X-XSS-Protection', '1; mode=block')
        response.headers.add('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        
        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Key')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        return response
    
    # 处理OPTIONS请求（预检请求）
    @app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def options_handler(path):
        return '', 204
    
    # 注册蓝图
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    # 启用CORS
    CORS(app)
    
    # 添加健康检查端点
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'ok',
            'timestamp': time.time()
        })
    
    # 添加错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': '请求的资源不存在'
        }), 404
        
    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"服务器错误: {error}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': '服务器内部错误'
        }), 500
        
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': '请求参数错误'
        }), 400
        
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': '未授权的请求'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': '禁止访问该资源'
        }), 403
    
    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({
            'success': False,
            'error': 'Too Many Requests',
            'message': '请求速率超限'
        }), 429
    
    # 添加JWT认证获取接口
    @app.route('/api/v1/auth/token', methods=['POST'])
    def get_token():
        username = request.json.get('username')
        password = request.json.get('password')
        
        # 检查用户名和密码（示例，实际使用应连接数据库验证）
        if username == app.config.get('ADMIN_USERNAME') and password == app.config.get('ADMIN_PASSWORD'):
            token = generate_jwt(
                user_id=username,
                role='admin',
                expires_in=app.config.get('JWT_EXPIRE_SECONDS')
            )
            if token:
                return jsonify({
                    'success': True,
                    'token': token,
                    'expires_in': app.config.get('JWT_EXPIRE_SECONDS')
                })
        
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': '用户名或密码错误'
        }), 401
    
    return app


# 简单测试
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0') 