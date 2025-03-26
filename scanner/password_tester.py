#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
弱密码尝试模块
"""

import logging
import random
import time
import os
from typing import Dict, List, Tuple, Optional, Any
import requests
import socket
import socks

logger = logging.getLogger(__name__)


class PasswordTester:
    """代理弱密码尝试器"""
    
    def __init__(self, config=None):
        """
        初始化密码尝试器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 超时设置
        self.timeout = self.config.get('timeout', 5)
        
        # 字典文件路径
        self.username_dict_file = self.config.get('username_dict_file', '')
        self.password_dict_file = self.config.get('password_dict_file', '')
        
        # 默认用户名和密码列表
        self.default_usernames = [
            'admin', 'root', 'user', 'proxy', 'guest', 'test', ''
        ]
        
        self.default_passwords = [
            'admin', 'password', '123456', 'root', 'admin123', 'proxy',
            '12345678', 'qwerty', '111111', '1234', 'test', ''
        ]
        
        # 从配置或字典文件加载用户名和密码
        self.usernames = self._load_usernames()
        self.passwords = self._load_passwords()
        
        # 测试URL
        self.test_url = self.config.get('test_url', 'http://httpbin.org/ip')
    
    def _load_usernames(self) -> List[str]:
        """
        从字典文件或配置加载用户名列表
        
        Returns:
            list: 用户名列表
        """
        # 首先尝试从文件加载
        if self.username_dict_file and os.path.exists(self.username_dict_file):
            try:
                logger.info(f"从字典文件加载用户名: {self.username_dict_file}")
                with open(self.username_dict_file, 'r', encoding='utf-8') as f:
                    # 过滤空行和注释行，去除空格
                    usernames = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                logger.info(f"从字典文件加载了 {len(usernames)} 个用户名")
                return usernames
            except Exception as e:
                logger.error(f"加载用户名字典文件失败: {str(e)}")
        
        # 否则从配置加载
        if 'usernames' in self.config:
            logger.info(f"从配置加载用户名列表，共 {len(self.config['usernames'])} 个")
            return self.config.get('usernames', [])
        
        # 如果以上都失败，使用默认列表
        logger.info(f"使用默认用户名列表，共 {len(self.default_usernames)} 个")
        return self.default_usernames
    
    def _load_passwords(self) -> List[str]:
        """
        从字典文件或配置加载密码列表
        
        Returns:
            list: 密码列表
        """
        # 首先尝试从文件加载
        if self.password_dict_file and os.path.exists(self.password_dict_file):
            try:
                logger.info(f"从字典文件加载密码: {self.password_dict_file}")
                with open(self.password_dict_file, 'r', encoding='utf-8') as f:
                    # 过滤空行和注释行，去除空格
                    passwords = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                logger.info(f"从字典文件加载了 {len(passwords)} 个密码")
                return passwords
            except Exception as e:
                logger.error(f"加载密码字典文件失败: {str(e)}")
        
        # 否则从配置加载
        if 'passwords' in self.config:
            logger.info(f"从配置加载密码列表，共 {len(self.config['passwords'])} 个")
            return self.config.get('passwords', [])
        
        # 如果以上都失败，使用默认列表
        logger.info(f"使用默认密码列表，共 {len(self.default_passwords)} 个")
        return self.default_passwords
    
    def test(self, ip: str, port: int, protocol: str) -> Optional[Dict[str, str]]:
        """
        测试代理的弱密码
        
        Args:
            ip: 代理IP
            port: 代理端口
            protocol: 代理协议（http, https, socks4, socks5）
            
        Returns:
            dict: 包含凭据的字典，如果没有找到有效凭据则返回None
        """
        logger.debug(f"开始对 {protocol}://{ip}:{port} 进行弱密码测试")
        
        # 生成凭据组合
        credentials = self._generate_credentials()
        
        # 根据协议选择测试方法
        if protocol in ['http', 'https']:
            return self._test_http_proxy(ip, port, credentials)
        elif protocol in ['socks4', 'socks5']:
            return self._test_socks_proxy(ip, port, protocol, credentials)
        else:
            logger.warning(f"不支持的协议: {protocol}")
            return None
    
    def _generate_credentials(self) -> List[Tuple[str, str]]:
        """
        生成凭据组合
        
        Returns:
            list: 用户名和密码组合列表
        """
        credentials = []
        
        # 先尝试无凭据
        credentials.append(('', ''))
        
        # 生成其他组合
        for username in self.usernames:
            for password in self.passwords:
                # 跳过空凭据组合（已添加）
                if username == '' and password == '':
                    continue
                credentials.append((username, password))
        
        # 随机打乱顺序
        random.shuffle(credentials)
        
        # 限制尝试数量，避免测试时间过长
        max_tries = self.config.get('max_credential_tries', 50)
        if max_tries > 0 and len(credentials) > max_tries:
            logger.info(f"凭据组合数量 {len(credentials)} 超过限制，随机选择 {max_tries} 个")
            credentials = credentials[:max_tries]
        
        logger.debug(f"生成了 {len(credentials)} 个凭据组合进行测试")
        return credentials
    
    def _test_http_proxy(self, ip: str, port: int, credentials: List[Tuple[str, str]]) -> Optional[Dict[str, str]]:
        """
        测试HTTP/HTTPS代理弱密码
        
        Args:
            ip: 代理IP
            port: 代理端口
            credentials: 凭据列表
            
        Returns:
            dict: 包含凭据的字典，如果没有找到有效凭据则返回None
        """
        for username, password in credentials:
            try:
                proxy_url = f"http://{ip}:{port}"
                
                # 设置代理
                if username and password:
                    proxies = {
                        'http': f"http://{username}:{password}@{ip}:{port}",
                        'https': f"http://{username}:{password}@{ip}:{port}"
                    }
                else:
                    proxies = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
                
                # 测试请求
                response = requests.get(
                    self.test_url,
                    proxies=proxies,
                    timeout=self.timeout
                )
                
                # 检查是否成功
                if response.status_code == 200:
                    logger.info(f"HTTP代理 {ip}:{port} 找到有效凭据: {username}:{password}")
                    return {
                        'username': username,
                        'password': password
                    }
                
            except Exception as e:
                logger.debug(f"HTTP代理 {ip}:{port} 凭据 {username}:{password} 测试失败: {str(e)}")
            
            # 随机延迟，避免触发防护
            time.sleep(random.uniform(0.1, 0.5))
        
        return None
    
    def _test_socks_proxy(self, ip: str, port: int, protocol: str, credentials: List[Tuple[str, str]]) -> Optional[Dict[str, str]]:
        """
        测试SOCKS代理弱密码
        
        Args:
            ip: 代理IP
            port: 代理端口
            protocol: 代理协议（socks4, socks5）
            credentials: 凭据列表
            
        Returns:
            dict: 包含凭据的字典，如果没有找到有效凭据则返回None
        """
        proxy_type = socks.SOCKS5 if protocol == 'socks5' else socks.SOCKS4
        
        for username, password in credentials:
            # 创建临时套接字并设置代理
            s = socks.socksocket()
            
            try:
                # 设置超时
                s.settimeout(self.timeout)
                
                # 设置代理
                s.set_proxy(
                    proxy_type=proxy_type,
                    addr=ip,
                    port=port,
                    username=username if username else None,
                    password=password if password else None
                )
                
                # 尝试连接一个常见网站（经常被访问且稳定的）
                s.connect(('www.google.com', 80))
                
                # 发送简单的HTTP请求
                s.sendall(b'GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n')
                
                # 接收响应
                data = s.recv(1024)
                
                # 如果收到了响应，说明代理有效
                if data:
                    logger.info(f"{protocol.upper()} 代理 {ip}:{port} 找到有效凭据: {username}:{password}")
                    return {
                        'username': username,
                        'password': password
                    }
                    
            except Exception as e:
                logger.debug(f"{protocol.upper()} 代理 {ip}:{port} 凭据 {username}:{password} 测试失败: {str(e)}")
            finally:
                # 关闭套接字
                s.close()
            
            # 随机延迟，避免触发防护
            time.sleep(random.uniform(0.1, 0.5))
        
        return None 