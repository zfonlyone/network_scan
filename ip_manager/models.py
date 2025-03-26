#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IP管理模块数据模型
"""

import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from database.connection import Base


class Proxy(Base):
    """代理IP模型"""
    
    __tablename__ = 'proxies'
    
    id = Column(Integer, primary_key=True)
    ip = Column(String(45), nullable=False, index=True)
    port = Column(Integer, nullable=False)
    protocol = Column(String(10), nullable=False, index=True)  # http, https, socks4, socks5
    username = Column(String(64), nullable=True)
    password = Column(String(64), nullable=True)
    
    country = Column(String(2), nullable=True, index=True)
    country_name = Column(String(64), nullable=True)
    region = Column(String(64), nullable=True)
    city = Column(String(64), nullable=True)
    
    is_anonymous = Column(Boolean, default=False, index=True)
    is_ssl = Column(Boolean, default=False)
    is_valid = Column(Boolean, default=True, index=True)
    
    response_time = Column(Float, nullable=True)  # 响应时间（秒）
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    
    last_checked = Column(DateTime, default=datetime.datetime.utcnow)
    last_successful = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    extra_data = Column(JSONB, nullable=True)  # 存储额外信息
    
    __table_args__ = (
        Index('idx_proxy_ip_port', 'ip', 'port', unique=True),
        Index('idx_proxy_protocol_is_valid', 'protocol', 'is_valid'),
        Index('idx_proxy_last_checked', 'last_checked'),
    )
    
    def __repr__(self):
        return f"<Proxy {self.protocol}://{self.ip}:{self.port}>"
    
    @property
    def connection_string(self):
        """获取连接字符串"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"{self.protocol}://{self.ip}:{self.port}"
    
    @property
    def success_ratio(self):
        """计算成功率"""
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'ip': self.ip,
            'port': self.port,
            'protocol': self.protocol,
            'username': self.username,
            'password': self.password,
            'country': self.country,
            'country_name': self.country_name,
            'region': self.region,
            'city': self.city,
            'is_anonymous': self.is_anonymous,
            'is_ssl': self.is_ssl,
            'is_valid': self.is_valid,
            'response_time': self.response_time,
            'success_count': self.success_count,
            'fail_count': self.fail_count,
            'success_ratio': self.success_ratio,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'last_successful': self.last_successful.isoformat() if self.last_successful else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ScanTarget(Base):
    """扫描目标模型"""
    
    __tablename__ = 'scan_targets'
    
    id = Column(Integer, primary_key=True)
    ip_range = Column(String(128), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    
    priority = Column(Integer, default=0, index=True)  # 优先级
    enabled = Column(Boolean, default=True, index=True)
    
    last_scanned = Column(DateTime, nullable=True)
    next_scan = Column(DateTime, nullable=True, index=True)
    scan_interval = Column(Integer, default=86400)  # 扫描间隔（秒）
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<ScanTarget {self.ip_range}>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'ip_range': self.ip_range,
            'description': self.description,
            'priority': self.priority,
            'enabled': self.enabled,
            'last_scanned': self.last_scanned.isoformat() if self.last_scanned else None,
            'next_scan': self.next_scan.isoformat() if self.next_scan else None,
            'scan_interval': self.scan_interval,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        } 