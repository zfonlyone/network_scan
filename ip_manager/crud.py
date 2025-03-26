#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IP管理模块数据库操作
"""

import logging
import datetime
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_session, close_session
from ip_manager.models import Proxy, ScanTarget

logger = logging.getLogger(__name__)


class ProxyCRUD:
    """代理IP CRUD操作"""
    
    @staticmethod
    def create_proxy(proxy_data):
        """
        创建代理IP记录
        
        Args:
            proxy_data: 代理数据字典
            
        Returns:
            Proxy: 创建的代理对象
        """
        session = get_session()
        try:
            proxy = Proxy(**proxy_data)
            session.add(proxy)
            session.commit()
            return proxy
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"创建代理记录失败: {str(e)}")
            raise
        finally:
            close_session(session)
            
    @staticmethod
    def get_proxy_by_id(proxy_id):
        """
        通过ID获取代理
        
        Args:
            proxy_id: 代理ID
            
        Returns:
            Proxy: 代理对象或None
        """
        session = get_session()
        try:
            return session.query(Proxy).filter(Proxy.id == proxy_id).first()
        finally:
            close_session(session)
            
    @staticmethod
    def get_proxy_by_ip_port(ip, port):
        """
        通过IP和端口获取代理
        
        Args:
            ip: IP地址
            port: 端口
            
        Returns:
            Proxy: 代理对象或None
        """
        session = get_session()
        try:
            return session.query(Proxy).filter(
                Proxy.ip == ip,
                Proxy.port == port
            ).first()
        finally:
            close_session(session)
            
    @staticmethod
    def update_proxy(proxy_id, update_data):
        """
        更新代理信息
        
        Args:
            proxy_id: 代理ID
            update_data: 更新数据字典
            
        Returns:
            bool: 更新是否成功
        """
        session = get_session()
        try:
            proxy = session.query(Proxy).filter(Proxy.id == proxy_id).first()
            if not proxy:
                return False
                
            for key, value in update_data.items():
                setattr(proxy, key, value)
                
            proxy.updated_at = datetime.datetime.utcnow()
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"更新代理记录失败: {str(e)}")
            return False
        finally:
            close_session(session)
            
    @staticmethod
    def delete_proxy(proxy_id):
        """
        删除代理
        
        Args:
            proxy_id: 代理ID
            
        Returns:
            bool: 删除是否成功
        """
        session = get_session()
        try:
            proxy = session.query(Proxy).filter(Proxy.id == proxy_id).first()
            if not proxy:
                return False
                
            session.delete(proxy)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"删除代理记录失败: {str(e)}")
            return False
        finally:
            close_session(session)
            
    @staticmethod
    def get_proxies(
        limit=100, 
        offset=0,
        protocol=None,
        is_valid=True,
        is_anonymous=None,
        country=None,
        max_response_time=None,
        min_success_ratio=None,
        order_by=None
    ):
        """
        获取代理列表
        
        Args:
            limit: 最大返回数量
            offset: 偏移量
            protocol: 协议筛选
            is_valid: 是否有效
            is_anonymous: 是否匿名
            country: 国家筛选
            max_response_time: 最大响应时间
            min_success_ratio: 最小成功率
            order_by: 排序字段
            
        Returns:
            list: 代理对象列表
        """
        session = get_session()
        try:
            query = session.query(Proxy)
            
            # 应用筛选条件
            if protocol is not None:
                query = query.filter(Proxy.protocol == protocol)
            
            if is_valid is not None:
                query = query.filter(Proxy.is_valid == is_valid)
                
            if is_anonymous is not None:
                query = query.filter(Proxy.is_anonymous == is_anonymous)
                
            if country is not None:
                query = query.filter(Proxy.country == country)
                
            if max_response_time is not None:
                query = query.filter(Proxy.response_time <= max_response_time)
                
            if min_success_ratio is not None:
                # 计算成功率并筛选
                total_checks = (Proxy.success_count + Proxy.fail_count)
                success_ratio = func.cast(Proxy.success_count, 'float') / func.nullif(total_checks, 0)
                query = query.filter(success_ratio >= min_success_ratio)
            
            # 应用排序
            if order_by == 'response_time':
                query = query.order_by(Proxy.response_time)
            elif order_by == 'success_count':
                query = query.order_by(Proxy.success_count.desc())
            elif order_by == 'last_checked':
                query = query.order_by(Proxy.last_checked.desc())
            else:
                # 默认排序：优先响应时间低且成功次数多的代理
                query = query.order_by(Proxy.response_time.asc(), Proxy.success_count.desc())
            
            return query.limit(limit).offset(offset).all()
        finally:
            close_session(session)
            
    @staticmethod
    def get_proxies_count(
        protocol=None,
        is_valid=True,
        is_anonymous=None,
        country=None,
    ):
        """获取代理数量"""
        session = get_session()
        try:
            query = session.query(func.count(Proxy.id))
            
            if protocol is not None:
                query = query.filter(Proxy.protocol == protocol)
            
            if is_valid is not None:
                query = query.filter(Proxy.is_valid == is_valid)
                
            if is_anonymous is not None:
                query = query.filter(Proxy.is_anonymous == is_anonymous)
                
            if country is not None:
                query = query.filter(Proxy.country == country)
                
            return query.scalar()
        finally:
            close_session(session)
            
    @staticmethod
    def get_proxies_for_check(limit=100, age_hours=6):
        """
        获取需要检查的代理
        
        Args:
            limit: 最大返回数量
            age_hours: 上次检查时间超过多少小时
            
        Returns:
            list: 代理对象列表
        """
        session = get_session()
        try:
            check_before = datetime.datetime.utcnow() - datetime.timedelta(hours=age_hours)
            
            query = session.query(Proxy).filter(
                or_(
                    Proxy.last_checked <= check_before,
                    Proxy.last_checked == None
                )
            ).order_by(Proxy.last_checked.asc())
            
            return query.limit(limit).all()
        finally:
            close_session(session)
            
    @staticmethod
    def update_proxy_status(proxy_id, is_valid, response_time=None, is_successful=False):
        """
        更新代理状态
        
        Args:
            proxy_id: 代理ID
            is_valid: 是否有效
            response_time: 响应时间
            is_successful: 是否成功
            
        Returns:
            bool: 更新是否成功
        """
        session = get_session()
        try:
            proxy = session.query(Proxy).filter(Proxy.id == proxy_id).first()
            if not proxy:
                return False
                
            proxy.is_valid = is_valid
            proxy.last_checked = datetime.datetime.utcnow()
            
            if response_time is not None:
                proxy.response_time = response_time
                
            if is_successful:
                proxy.success_count += 1
                proxy.last_successful = datetime.datetime.utcnow()
            else:
                proxy.fail_count += 1
                
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"更新代理状态失败: {str(e)}")
            return False
        finally:
            close_session(session)
            
    @staticmethod
    def upsert_proxy(ip, port, protocol, extra_data=None):
        """
        插入或更新代理信息
        
        Args:
            ip: IP地址
            port: 端口
            protocol: 协议
            extra_data: 额外数据
            
        Returns:
            Proxy: 代理对象
        """
        session = get_session()
        try:
            proxy = session.query(Proxy).filter(
                Proxy.ip == ip,
                Proxy.port == port
            ).first()
            
            if proxy:
                # 更新现有记录
                proxy.protocol = protocol
                if extra_data:
                    for key, value in extra_data.items():
                        if hasattr(proxy, key):
                            setattr(proxy, key, value)
                            
                proxy.updated_at = datetime.datetime.utcnow()
            else:
                # 创建新记录
                proxy_data = {
                    'ip': ip,
                    'port': port,
                    'protocol': protocol
                }
                if extra_data:
                    proxy_data.update(extra_data)
                    
                proxy = Proxy(**proxy_data)
                session.add(proxy)
                
            session.commit()
            return proxy
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"插入或更新代理失败: {str(e)}")
            raise
        finally:
            close_session(session)


class ScanTargetCRUD:
    """扫描目标CRUD操作"""
    
    @staticmethod
    def create_target(target_data):
        """创建扫描目标"""
        session = get_session()
        try:
            target = ScanTarget(**target_data)
            session.add(target)
            session.commit()
            return target
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"创建扫描目标失败: {str(e)}")
            raise
        finally:
            close_session(session)
            
    @staticmethod
    def get_target_by_id(target_id):
        """通过ID获取扫描目标"""
        session = get_session()
        try:
            return session.query(ScanTarget).filter(ScanTarget.id == target_id).first()
        finally:
            close_session(session)
            
    @staticmethod
    def get_target_by_ip_range(ip_range):
        """通过IP范围获取扫描目标"""
        session = get_session()
        try:
            return session.query(ScanTarget).filter(ScanTarget.ip_range == ip_range).first()
        finally:
            close_session(session)
            
    @staticmethod
    def update_target(target_id, update_data):
        """更新扫描目标"""
        session = get_session()
        try:
            target = session.query(ScanTarget).filter(ScanTarget.id == target_id).first()
            if not target:
                return False
                
            for key, value in update_data.items():
                setattr(target, key, value)
                
            target.updated_at = datetime.datetime.utcnow()
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"更新扫描目标失败: {str(e)}")
            return False
        finally:
            close_session(session)
            
    @staticmethod
    def delete_target(target_id):
        """删除扫描目标"""
        session = get_session()
        try:
            target = session.query(ScanTarget).filter(ScanTarget.id == target_id).first()
            if not target:
                return False
                
            session.delete(target)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"删除扫描目标失败: {str(e)}")
            return False
        finally:
            close_session(session)
            
    @staticmethod
    def get_targets(limit=100, offset=0, enabled_only=True):
        """获取扫描目标列表"""
        session = get_session()
        try:
            query = session.query(ScanTarget)
            
            if enabled_only:
                query = query.filter(ScanTarget.enabled == True)
                
            query = query.order_by(ScanTarget.priority.desc())
            
            return query.limit(limit).offset(offset).all()
        finally:
            close_session(session)
            
    @staticmethod
    def get_targets_for_scan(limit=10):
        """获取待扫描的目标"""
        session = get_session()
        try:
            now = datetime.datetime.utcnow()
            
            query = session.query(ScanTarget).filter(
                ScanTarget.enabled == True,
                or_(
                    ScanTarget.next_scan <= now,
                    ScanTarget.next_scan == None
                )
            ).order_by(ScanTarget.priority.desc(), ScanTarget.next_scan.asc())
            
            return query.limit(limit).all()
        finally:
            close_session(session)
            
    @staticmethod
    def update_scan_status(target_id, last_scanned=None):
        """更新扫描状态"""
        session = get_session()
        try:
            target = session.query(ScanTarget).filter(ScanTarget.id == target_id).first()
            if not target:
                return False
                
            if last_scanned is None:
                last_scanned = datetime.datetime.utcnow()
                
            target.last_scanned = last_scanned
            
            # 计算下次扫描时间
            target.next_scan = last_scanned + datetime.timedelta(seconds=target.scan_interval)
            
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"更新扫描状态失败: {str(e)}")
            return False
        finally:
            close_session(session) 