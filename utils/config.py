#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件加载模块
"""

import os
import yaml
import logging

logger = logging.getLogger(__name__)


def load_config(config_path):
    """
    从YAML文件加载配置
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        dict: 配置字典
    """
    try:
        if not os.path.exists(config_path):
            logger.warning(f"配置文件不存在: {config_path}, 使用默认配置")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # 处理环境变量替换
        _process_env_vars(config)
        
        logger.info(f"成功加载配置文件: {config_path}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return {}


def _process_env_vars(config):
    """
    处理配置中的环境变量引用
    
    Args:
        config: 配置字典或其一部分
    """
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                env_value = os.environ.get(env_var)
                if env_value is not None:
                    config[key] = env_value
                else:
                    logger.warning(f"环境变量未定义: {env_var}")
            elif isinstance(value, (dict, list)):
                _process_env_vars(value)
    elif isinstance(config, list):
        for i, item in enumerate(config):
            if isinstance(item, (dict, list)):
                _process_env_vars(item)
            elif isinstance(item, str) and item.startswith('${') and item.endswith('}'):
                env_var = item[2:-1]
                env_value = os.environ.get(env_var)
                if env_value is not None:
                    config[i] = env_value
                else:
                    logger.warning(f"环境变量未定义: {env_var}")


def get_config_value(config, path, default=None):
    """
    从配置字典中获取嵌套值
    
    Args:
        config: 配置字典
        path: 点分隔的路径，如 "database.host"
        default: 默认值，如果路径不存在
        
    Returns:
        找到的值或默认值
    """
    if not config:
        return default
        
    keys = path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
            
    return value 