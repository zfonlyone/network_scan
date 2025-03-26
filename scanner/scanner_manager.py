#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
扫描器管理模块
"""

import logging
import threading
import time
import queue
import datetime
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from ip_manager.crud import ProxyCRUD, ScanTargetCRUD
from scanner.ip_generator import IPGenerator
from scanner.port_scanner import PortScanner
from scanner.proxy_checker import ProxyChecker
from utils.logging import get_logger

logger = get_logger(__name__)


class ScannerManager:
    """扫描管理器"""
    
    def __init__(self, config=None):
        """
        初始化扫描管理器
        
        Args:
            config: 扫描配置字典
        """
        self.config = config or {}
        self.running = False
        self.scan_thread = None
        self.check_thread = None
        self.scan_interval = self.config.get('scan_interval', 3600)  # 扫描间隔（秒）
        self.check_interval = self.config.get('check_interval', 600)  # 检查间隔（秒）
        self.max_workers = self.config.get('max_workers', 10)  # 最大工作线程数
        self.max_scan_targets = self.config.get('max_scan_targets', 5)  # 单次最大扫描目标数
        self.max_check_proxies = self.config.get('max_check_proxies', 100)  # 单次最大检查代理数
        self.proxy_age_hours = self.config.get('proxy_age_hours', 6)  # 代理检查周期（小时）
        
        # 复制外部字典文件（如果存在）
        self._copy_dict_files()
        
        # 创建组件
        self.ip_generator = IPGenerator()
        self.port_scanner = PortScanner(self.config.get('port_scanner', {}))
        self.proxy_checker = ProxyChecker(self.config.get('proxy_checker', {}))
        
        # 创建任务队列
        self.port_queue = queue.Queue()
        self.check_queue = queue.Queue()
    
    def _copy_dict_files(self):
        """复制外部字典文件到应用目录"""
        src_dir = '/app/dict_src'  # 外部挂载的源字典目录
        dst_dir = '/app/dict'      # 应用内字典目录
        
        # 如果源目录存在且有文件
        if os.path.exists(src_dir) and os.path.isdir(src_dir):
            logger.info(f"检测到外部字典目录: {src_dir}")
            try:
                # 复制用户名字典
                username_files = [f for f in os.listdir(src_dir) if 'username' in f.lower() and f.endswith('.txt')]
                if username_files:
                    src_file = os.path.join(src_dir, username_files[0])
                    dst_file = os.path.join(dst_dir, 'usernames.txt')
                    shutil.copy2(src_file, dst_file)
                    logger.info(f"已复制用户名字典: {src_file} -> {dst_file}")
                
                # 复制密码字典
                password_files = [f for f in os.listdir(src_dir) if 'password' in f.lower() and f.endswith('.txt')]
                if password_files:
                    src_file = os.path.join(src_dir, password_files[0])
                    dst_file = os.path.join(dst_dir, 'passwords.txt')
                    shutil.copy2(src_file, dst_file)
                    logger.info(f"已复制密码字典: {src_file} -> {dst_file}")
                    
            except Exception as e:
                logger.error(f"复制字典文件时出错: {str(e)}")
    
    def start(self):
        """启动扫描管理器"""
        if self.running:
            logger.warning("扫描管理器已经在运行")
            return
            
        self.running = True
        
        # 启动扫描线程
        self.scan_thread = threading.Thread(target=self._scan_worker, name="ScanWorker")
        self.scan_thread.daemon = True
        self.scan_thread.start()
        
        # 启动检查线程
        self.check_thread = threading.Thread(target=self._check_worker, name="CheckWorker")
        self.check_thread.daemon = True
        self.check_thread.start()
        
        logger.info("扫描管理器已启动")
    
    def stop(self):
        """停止扫描管理器"""
        if not self.running:
            logger.warning("扫描管理器未运行")
            return
            
        self.running = False
        
        # 等待线程结束
        if self.scan_thread:
            self.scan_thread.join(timeout=5)
            
        if self.check_thread:
            self.check_thread.join(timeout=5)
            
        logger.info("扫描管理器已停止")
    
    def _scan_worker(self):
        """扫描工作线程"""
        logger.info("扫描工作线程已启动")
        
        while self.running:
            try:
                # 获取待扫描的目标
                targets = ScanTargetCRUD.get_targets_for_scan(limit=self.max_scan_targets)
                
                if not targets:
                    logger.info("没有待扫描的目标，等待下一轮扫描")
                    time.sleep(self.scan_interval)
                    continue
                
                logger.info(f"找到 {len(targets)} 个待扫描目标")
                
                for target in targets:
                    try:
                        # 更新扫描状态
                        ScanTargetCRUD.update_scan_status(target.id)
                        
                        # 生成IP
                        ip_list = self.ip_generator.generate(target.ip_range)
                        logger.info(f"为目标 {target.ip_range} 生成了 {len(ip_list)} 个IP地址")
                        
                        # 扫描端口
                        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                            for ip in ip_list:
                                # 提交扫描任务
                                executor.submit(self._scan_ip, ip)
                        
                        logger.info(f"目标 {target.ip_range} 扫描完成")
                        
                    except Exception as e:
                        logger.error(f"扫描目标 {target.ip_range} 失败: {str(e)}", exc_info=True)
                
                # 等待下一轮扫描
                time.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"扫描工作线程异常: {str(e)}", exc_info=True)
                time.sleep(60)  # 发生异常时等待一分钟
    
    def _check_worker(self):
        """代理检查工作线程"""
        logger.info("代理检查工作线程已启动")
        
        while self.running:
            try:
                # 获取待检查的代理
                proxies = ProxyCRUD.get_proxies_for_check(
                    limit=self.max_check_proxies,
                    age_hours=self.proxy_age_hours
                )
                
                if not proxies:
                    logger.info("没有待检查的代理，等待下一轮检查")
                    time.sleep(self.check_interval)
                    continue
                
                logger.info(f"找到 {len(proxies)} 个待检查代理")
                
                # 检查代理
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    for proxy in proxies:
                        # 提交检查任务
                        executor.submit(self._check_proxy, proxy)
                
                # 等待下一轮检查
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"代理检查工作线程异常: {str(e)}", exc_info=True)
                time.sleep(60)  # 发生异常时等待一分钟
    
    def _scan_ip(self, ip):
        """
        扫描单个IP的所有端口
        
        Args:
            ip: IP地址
        """
        try:
            logger.debug(f"开始扫描IP: {ip}")
            
            # 扫描端口
            open_ports = self.port_scanner.scan(ip)
            
            if not open_ports:
                logger.debug(f"IP {ip} 没有开放端口")
                return
                
            logger.info(f"IP {ip} 发现 {len(open_ports)} 个开放端口: {open_ports}")
            
            # 检查每个开放端口
            for port in open_ports:
                # 测试代理
                results = self.proxy_checker.check(ip, port)
                
                if not results:
                    logger.debug(f"IP {ip}:{port} 不是有效代理")
                    continue
                
                # 保存到数据库
                for protocol, result in results.items():
                    if result['is_valid']:
                        try:
                            # 提取身份验证信息
                            username = result.get('username', '')
                            password = result.get('password', '')
                            auth_required = result.get('auth_required', False)
                            
                            ProxyCRUD.upsert_proxy(
                                ip=ip,
                                port=port,
                                protocol=protocol,
                                extra_data={
                                    'is_valid': result['is_valid'],
                                    'is_anonymous': result.get('is_anonymous', False),
                                    'response_time': result.get('response_time'),
                                    'country': result.get('country'),
                                    'country_name': result.get('country_name'),
                                    'region': result.get('region'),
                                    'city': result.get('city'),
                                    'auth_required': auth_required,
                                    'username': username,
                                    'password': password,
                                    'last_checked': datetime.datetime.utcnow(),
                                    'last_successful': datetime.datetime.utcnow(),
                                    'success_count': 1,
                                }
                            )
                            logger.info(f"IP {ip}:{port} 已作为 {protocol} 代理保存，认证：{'需要' if auth_required else '不需要'}")
                            
                        except Exception as e:
                            logger.error(f"保存代理 {ip}:{port} 失败: {str(e)}")
        
        except Exception as e:
            logger.error(f"扫描IP {ip} 失败: {str(e)}")
    
    def _check_proxy(self, proxy):
        """
        检查单个代理
        
        Args:
            proxy: 代理对象
        """
        try:
            logger.debug(f"开始检查代理: {proxy.ip}:{proxy.port}")
            
            # 检查代理
            result = self.proxy_checker.check_proxy(
                proxy.ip, 
                proxy.port, 
                proxy.protocol
            )
            
            # 更新代理状态
            ProxyCRUD.update_proxy_status(
                proxy_id=proxy.id,
                is_valid=result['is_valid'],
                response_time=result.get('response_time'),
                is_successful=result['is_valid']
            )
            
            status = "有效" if result['is_valid'] else "无效"
            logger.debug(f"代理 {proxy.ip}:{proxy.port} 检查完成，状态: {status}")
            
        except Exception as e:
            logger.error(f"检查代理 {proxy.ip}:{proxy.port} 失败: {str(e)}")
            
            # 更新为无效状态
            try:
                ProxyCRUD.update_proxy_status(
                    proxy_id=proxy.id,
                    is_valid=False,
                    is_successful=False
                )
            except Exception as e2:
                logger.error(f"更新代理状态失败: {str(e2)}") 