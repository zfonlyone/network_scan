#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库连接管理模块
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)

# 全局变量
_engine = None
_SessionFactory = None
Base = declarative_base()


def init_db(config):
    """
    初始化数据库连接
    
    Args:
        config: 数据库配置字典
    """
    global _engine, _SessionFactory
    
    try:
        # 构建数据库连接URL
        username = config.get('username', 'postgres')
        password = config.get('password', '')
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        database = config.get('database', 'proxy_scanner')
        
        db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        
        # 创建引擎
        _engine = create_engine(
            db_url,
            echo=config.get('echo', False),
            pool_size=config.get('pool_size', 5),
            max_overflow=config.get('max_overflow', 10),
            pool_timeout=config.get('pool_timeout', 30),
            pool_recycle=config.get('pool_recycle', 3600),
        )
        
        # 创建会话工厂
        _SessionFactory = scoped_session(sessionmaker(bind=_engine))
        
        logger.info(f"数据库连接已初始化: {host}:{port}/{database}")
        
        # 如果配置了自动创建表，则创建所有表
        if config.get('create_tables', False):
            Base.metadata.create_all(_engine)
            logger.info("数据库表已创建")
            
    except Exception as e:
        logger.error(f"初始化数据库连接失败: {str(e)}", exc_info=True)
        raise


def get_session():
    """
    获取数据库会话
    
    Returns:
        sqlalchemy.orm.Session: 数据库会话对象
    
    Raises:
        RuntimeError: 如果数据库未初始化
    """
    if _SessionFactory is None:
        raise RuntimeError("数据库未初始化, 请先调用init_db")
    return _SessionFactory()


def close_session(session):
    """
    关闭数据库会话
    
    Args:
        session: 数据库会话对象
    """
    if session:
        session.close()


def get_engine():
    """
    获取数据库引擎
    
    Returns:
        sqlalchemy.engine.Engine: 数据库引擎
    
    Raises:
        RuntimeError: 如果数据库未初始化
    """
    if _engine is None:
        raise RuntimeError("数据库未初始化, 请先调用init_db")
    return _engine 