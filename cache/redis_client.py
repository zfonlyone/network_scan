#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis缓存客户端模块
"""

import logging
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# 全局变量
_redis_client = None
_redis_config = None


def init_redis(config):
    """
    初始化Redis连接
    
    Args:
        config: Redis配置字典
    """
    global _redis_client, _redis_config
    
    try:
        _redis_config = config
        
        host = config.get('host', 'localhost')
        port = config.get('port', 6379)
        db = config.get('db', 0)
        password = config.get('password', None)
        socket_timeout = config.get('socket_timeout', 5)
        socket_connect_timeout = config.get('socket_connect_timeout', 5)
        
        _redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=True,  # 自动将字节解码为字符串
        )
        
        # 测试连接
        _redis_client.ping()
        
        logger.info(f"Redis连接已初始化: {host}:{port}/{db}")
        
    except RedisError as e:
        logger.error(f"初始化Redis连接失败: {str(e)}", exc_info=True)
        _redis_client = None
        raise


def get_redis():
    """
    获取Redis客户端
    
    Returns:
        redis.Redis: Redis客户端对象
    
    Raises:
        RuntimeError: 如果Redis未初始化
    """
    if _redis_client is None:
        raise RuntimeError("Redis未初始化, 请先调用init_redis")
    return _redis_client


def get_or_init_redis(config=None):
    """
    获取Redis客户端，如果未初始化则使用提供的配置初始化
    
    Args:
        config: Redis配置字典，如果为None则使用上次的配置
        
    Returns:
        redis.Redis: Redis客户端对象
    """
    global _redis_client
    
    if _redis_client is None:
        if config is None:
            if _redis_config is None:
                raise RuntimeError("Redis未初始化且未提供配置")
            config = _redis_config
        init_redis(config)
        
    return _redis_client


class RedisCache:
    """Redis缓存操作封装类"""
    
    def __init__(self, prefix="proxy"):
        """
        初始化
        
        Args:
            prefix: 键前缀
        """
        self.prefix = prefix
        self.redis = get_redis()
        
    def _get_key(self, key):
        """获取带前缀的键名"""
        return f"{self.prefix}:{key}"
        
    def set(self, key, value, expire=None):
        """
        设置缓存
        
        Args:
            key: 键名
            value: 值
            expire: 过期时间（秒）
        
        Returns:
            bool: 操作是否成功
        """
        try:
            full_key = self._get_key(key)
            if expire:
                return self.redis.setex(full_key, expire, value)
            else:
                return self.redis.set(full_key, value)
        except RedisError as e:
            logger.error(f"Redis设置键失败: {key}, {str(e)}")
            return False
            
    def get(self, key, default=None):
        """
        获取缓存
        
        Args:
            key: 键名
            default: 默认值
        
        Returns:
            缓存值或默认值
        """
        try:
            full_key = self._get_key(key)
            value = self.redis.get(full_key)
            return value if value is not None else default
        except RedisError as e:
            logger.error(f"Redis获取键失败: {key}, {str(e)}")
            return default
            
    def delete(self, key):
        """
        删除缓存
        
        Args:
            key: 键名
        
        Returns:
            int: 删除的键数量
        """
        try:
            full_key = self._get_key(key)
            return self.redis.delete(full_key)
        except RedisError as e:
            logger.error(f"Redis删除键失败: {key}, {str(e)}")
            return 0
            
    def exists(self, key):
        """
        检查键是否存在
        
        Args:
            key: 键名
        
        Returns:
            bool: 键是否存在
        """
        try:
            full_key = self._get_key(key)
            return bool(self.redis.exists(full_key))
        except RedisError as e:
            logger.error(f"Redis检查键失败: {key}, {str(e)}")
            return False
            
    def incr(self, key, amount=1):
        """
        增加计数器
        
        Args:
            key: 键名
            amount: 增加量
        
        Returns:
            int: 增加后的值
        """
        try:
            full_key = self._get_key(key)
            return self.redis.incrby(full_key, amount)
        except RedisError as e:
            logger.error(f"Redis增加计数器失败: {key}, {str(e)}")
            return 0
            
    def expire(self, key, seconds):
        """
        设置过期时间
        
        Args:
            key: 键名
            seconds: 过期秒数
        
        Returns:
            bool: 操作是否成功
        """
        try:
            full_key = self._get_key(key)
            return self.redis.expire(full_key, seconds)
        except RedisError as e:
            logger.error(f"Redis设置过期时间失败: {key}, {str(e)}")
            return False 