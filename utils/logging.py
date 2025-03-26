#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志配置模块
"""

import os
import logging
import logging.config
from datetime import datetime


def setup_logging(config=None, debug=False):
    """
    设置日志系统
    
    Args:
        config: 日志配置字典
        debug: 是否启用调试模式
    """
    if config is None:
        config = {}
    
    # 确保日志目录存在
    log_dir = config.get('log_dir', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'proxy_scanner_{timestamp}.log')
    
    # 默认日志配置
    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG' if debug else 'INFO',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': log_file,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console', 'file'],
                'level': 'DEBUG' if debug else 'INFO',
                'propagate': True
            }
        }
    }
    
    # 用用户配置覆盖默认配置
    if 'formatters' in config:
        log_config['formatters'].update(config.get('formatters', {}))
    if 'handlers' in config:
        log_config['handlers'].update(config.get('handlers', {}))
    if 'loggers' in config:
        log_config['loggers'].update(config.get('loggers', {}))
    
    # 应用配置
    logging.config.dictConfig(log_config)
    
    # 如果是调试模式，设置第三方库的日志级别为WARNING以减少噪音
    if debug:
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.INFO)


def get_logger(name):
    """
    获取命名的日志记录器
    
    Args:
        name: 记录器名称
    
    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name) 