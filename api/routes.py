#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API路由模块，定义所有API端点
"""

from flask import Blueprint, request, jsonify, current_app, g
from api.auth import require_auth
from database.database import get_db_session
from utils.logging import get_logger
from ip_manager.proxy_manager import ProxyManager

# 创建蓝图
api_bp = Blueprint('api', __name__)
logger = get_logger(__name__)


@api_bp.route('/proxies', methods=['GET'])
@require_auth
def get_proxies():
    """
    获取代理IP列表

    查询参数:
    - country: 国家/地区代码
    - type: 代理类型 (http/https/socks4/socks5)
    - anonymity: 匿名级别 (transparent/anonymous/high_anonymous)
    - limit: 返回结果数量限制
    - page: 分页页码
    - sort_by: 排序字段
    - sort_order: 排序方向 (asc/desc)
    - min_score: 最小评分
    - active_within: 最近活跃时间（小时）
    - export: 导出格式 (json/csv/txt)
    
    返回:
    - proxies: 代理IP列表
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页记录数
    """
    try:
        # 获取查询参数
        country = request.args.get('country')
        proxy_type = request.args.get('type')
        anonymity = request.args.get('anonymity')
        limit = int(request.args.get('limit', 100))
        page = int(request.args.get('page', 1))
        sort_by = request.args.get('sort_by', 'score')
        sort_order = request.args.get('sort_order', 'desc')
        min_score = int(request.args.get('min_score', 0))
        active_within = request.args.get('active_within')
        export_format = request.args.get('export')
        
        # 创建数据库会话
        with get_db_session() as session:
            proxy_manager = ProxyManager(session)
            
            # 获取代理列表
            proxies, total = proxy_manager.get_proxies(
                country=country,
                proxy_type=proxy_type,
                anonymity=anonymity,
                limit=limit,
                page=page,
                sort_by=sort_by,
                sort_order=sort_order,
                min_score=min_score,
                active_within=active_within
            )
            
            # 转换为字典列表
            proxy_list = [p.to_dict() for p in proxies]
            
            # 记录API使用情况
            client_ip = g.client_ip
            auth_method = getattr(g, 'auth_method', 'unknown')
            user_id = getattr(g, 'user_id', None)
            logger.info(f"获取代理列表: IP={client_ip}, 认证方式={auth_method}, 用户={user_id}, 结果数量={len(proxy_list)}")
            
            # 处理导出请求
            if export_format:
                return proxy_manager.export_proxies(
                    proxies=proxy_list,
                    export_format=export_format
                )
            
            # 返回JSON结果
            return jsonify({
                'success': True,
                'proxies': proxy_list,
                'total': total,
                'page': page,
                'page_size': limit
            })
            
    except Exception as e:
        logger.error(f"获取代理列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'获取代理列表失败: {str(e)}'
        }), 500


@api_bp.route('/proxies/<int:proxy_id>', methods=['GET'])
@require_auth
def get_proxy(proxy_id):
    """
    获取单个代理IP详情
    
    参数:
    - proxy_id: 代理ID
    
    返回:
    - proxy: 代理详情
    """
    try:
        # 创建数据库会话
        with get_db_session() as session:
            proxy_manager = ProxyManager(session)
            
            # 获取代理详情
            proxy = proxy_manager.get_proxy_by_id(proxy_id)
            
            if not proxy:
                return jsonify({
                    'success': False,
                    'error': 'Not Found',
                    'message': f'代理ID {proxy_id} 不存在'
                }), 404
                
            # 记录API使用情况
            client_ip = g.client_ip
            auth_method = getattr(g, 'auth_method', 'unknown')
            user_id = getattr(g, 'user_id', None)
            logger.info(f"获取代理详情: ID={proxy_id}, IP={client_ip}, 认证方式={auth_method}, 用户={user_id}")
            
            # 返回结果
            return jsonify({
                'success': True,
                'proxy': proxy.to_dict(include_history=True)
            })
            
    except Exception as e:
        logger.error(f"获取代理详情失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'获取代理详情失败: {str(e)}'
        }), 500


@api_bp.route('/proxies/stats', methods=['GET'])
@require_auth
def get_stats():
    """
    获取代理统计信息
    
    返回:
    - total: 总代理数
    - available: 可用代理数
    - by_country: 按国家/地区统计
    - by_type: 按类型统计
    - by_anonymity: 按匿名级别统计
    """
    try:
        # 创建数据库会话
        with get_db_session() as session:
            proxy_manager = ProxyManager(session)
            
            # 获取统计信息
            stats = proxy_manager.get_stats()
            
            # 记录API使用情况
            client_ip = g.client_ip
            auth_method = getattr(g, 'auth_method', 'unknown')
            user_id = getattr(g, 'user_id', None)
            logger.info(f"获取代理统计: IP={client_ip}, 认证方式={auth_method}, 用户={user_id}")
            
            # 返回结果
            return jsonify({
                'success': True,
                'stats': stats
            })
            
    except Exception as e:
        logger.error(f"获取代理统计失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'获取代理统计失败: {str(e)}'
        }), 500


@api_bp.route('/proxies/random', methods=['GET'])
@require_auth
def get_random_proxy():
    """
    获取随机代理
    
    查询参数:
    - country: 国家/地区代码
    - type: 代理类型 (http/https/socks4/socks5)
    - anonymity: 匿名级别 (transparent/anonymous/high_anonymous)
    - min_score: 最小评分
    
    返回:
    - proxy: 随机代理
    """
    try:
        # 获取查询参数
        country = request.args.get('country')
        proxy_type = request.args.get('type')
        anonymity = request.args.get('anonymity')
        min_score = int(request.args.get('min_score', 50))
        
        # 创建数据库会话
        with get_db_session() as session:
            proxy_manager = ProxyManager(session)
            
            # 获取随机代理
            proxy = proxy_manager.get_random_proxy(
                country=country,
                proxy_type=proxy_type,
                anonymity=anonymity,
                min_score=min_score
            )
            
            if not proxy:
                return jsonify({
                    'success': False,
                    'error': 'Not Found',
                    'message': '未找到符合条件的代理'
                }), 404
                
            # 记录API使用情况
            client_ip = g.client_ip
            auth_method = getattr(g, 'auth_method', 'unknown')
            user_id = getattr(g, 'user_id', None)
            logger.info(f"获取随机代理: IP={client_ip}, 认证方式={auth_method}, 用户={user_id}, 代理ID={proxy.id}")
            
            # 返回结果
            return jsonify({
                'success': True,
                'proxy': proxy.to_dict()
            })
            
    except Exception as e:
        logger.error(f"获取随机代理失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'获取随机代理失败: {str(e)}'
        }), 500


@api_bp.route('/proxies/verify', methods=['POST'])
@require_auth
def verify_proxy():
    """
    验证代理可用性
    
    请求体:
    - proxy: 代理地址(ip:port)
    - type: 代理类型 (http/https/socks4/socks5)
    - username: 用户名 (可选)
    - password: 密码 (可选)
    
    返回:
    - success: 是否成功
    - is_valid: 代理是否有效
    - details: 验证详情
    """
    try:
        # 获取请求数据
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': '缺少请求数据'
            }), 400
            
        proxy = data.get('proxy')
        proxy_type = data.get('type', 'http')
        username = data.get('username')
        password = data.get('password')
        
        if not proxy:
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': '缺少代理地址'
            }), 400
            
        # 创建数据库会话
        with get_db_session() as session:
            proxy_manager = ProxyManager(session)
            
            # 验证代理
            is_valid, details = proxy_manager.verify_external_proxy(
                proxy=proxy,
                proxy_type=proxy_type,
                username=username,
                password=password
            )
            
            # 记录API使用情况
            client_ip = g.client_ip
            auth_method = getattr(g, 'auth_method', 'unknown')
            user_id = getattr(g, 'user_id', None)
            logger.info(f"验证代理: IP={client_ip}, 认证方式={auth_method}, 用户={user_id}, 代理={proxy}, 结果={is_valid}")
            
            # 返回结果
            return jsonify({
                'success': True,
                'is_valid': is_valid,
                'details': details
            })
            
    except Exception as e:
        logger.error(f"验证代理失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'验证代理失败: {str(e)}'
        }), 500


@api_bp.route('/proxies/report', methods=['POST'])
@require_auth
def report_proxy():
    """
    报告代理状态
    
    请求体:
    - proxy_id: 代理ID
    - status: 状态 (success/failure)
    - details: 详细信息 (可选)
    
    返回:
    - success: 是否成功
    """
    try:
        # 获取请求数据
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': '缺少请求数据'
            }), 400
            
        proxy_id = data.get('proxy_id')
        status = data.get('status')
        details = data.get('details', {})
        
        if not proxy_id or not status:
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': '缺少必要参数'
            }), 400
            
        if status not in ['success', 'failure']:
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': '状态值无效'
            }), 400
            
        # 创建数据库会话
        with get_db_session() as session:
            proxy_manager = ProxyManager(session)
            
            # 更新代理状态
            result = proxy_manager.update_proxy_status(
                proxy_id=proxy_id,
                status=status,
                details=details
            )
            
            if not result:
                return jsonify({
                    'success': False,
                    'error': 'Not Found',
                    'message': f'代理ID {proxy_id} 不存在'
                }), 404
                
            # 记录API使用情况
            client_ip = g.client_ip
            auth_method = getattr(g, 'auth_method', 'unknown')
            user_id = getattr(g, 'user_id', None)
            logger.info(f"报告代理状态: IP={client_ip}, 认证方式={auth_method}, 用户={user_id}, 代理ID={proxy_id}, 状态={status}")
            
            # 返回结果
            return jsonify({
                'success': True,
                'message': f'代理状态已更新'
            })
            
    except Exception as e:
        logger.error(f"报告代理状态失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'报告代理状态失败: {str(e)}'
        }), 500


@api_bp.route('/proxies/countries', methods=['GET'])
@require_auth
def get_countries():
    """
    获取代理IP的国家/地区列表
    
    返回:
    - countries: 国家/地区列表，包含代码和名称
    """
    try:
        # 创建数据库会话
        with get_db_session() as session:
            proxy_manager = ProxyManager(session)
            
            # 获取国家/地区列表
            countries = proxy_manager.get_countries()
            
            # 记录API使用情况
            client_ip = g.client_ip
            auth_method = getattr(g, 'auth_method', 'unknown')
            user_id = getattr(g, 'user_id', None)
            logger.info(f"获取国家/地区列表: IP={client_ip}, 认证方式={auth_method}, 用户={user_id}")
            
            # 返回结果
            return jsonify({
                'success': True,
                'countries': countries
            })
            
    except Exception as e:
        logger.error(f"获取国家/地区列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'获取国家/地区列表失败: {str(e)}'
        }), 500


@api_bp.route('/system/status', methods=['GET'])
@require_auth
def get_system_status():
    """
    获取系统状态
    
    返回:
    - status: 系统状态
    - version: 系统版本
    - uptime: 系统运行时间
    - scanner_status: 扫描器状态
    - database_status: 数据库状态
    """
    try:
        # 创建数据库会话
        with get_db_session() as session:
            # 这里需要实现系统状态检查逻辑
            status = {
                'status': 'running',
                'version': '1.0.0',
                'uptime': '3 days, 12 hours',
                'scanner_status': 'running',
                'database_status': 'connected',
                'proxy_count': 1000,
                'last_scan': '2023-03-26 10:30:00',
                'next_scan': '2023-03-26 11:30:00'
            }
            
            # 记录API使用情况
            client_ip = g.client_ip
            auth_method = getattr(g, 'auth_method', 'unknown')
            user_id = getattr(g, 'user_id', None)
            logger.info(f"获取系统状态: IP={client_ip}, 认证方式={auth_method}, 用户={user_id}")
            
            # 返回结果
            return jsonify({
                'success': True,
                'system': status
            })
            
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'获取系统状态失败: {str(e)}'
        }), 500 