#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理检查器模块
"""

import logging
import time
import socket
import requests
import threading
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from scanner.password_tester import PasswordTester

logger = logging.getLogger(__name__)


class ProxyChecker:
    """代理检查器"""
    
    def __init__(self, config=None):
        """
        初始化代理检查器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 超时设置
        self.timeout = self.config.get('timeout', 5)
        
        # 测试网站
        self.test_urls = self.config.get('test_urls', [
            'http://httpbin.org/ip',
            'http://ifconfig.me/ip',
            'http://api.ipify.org'
        ])
        
        # 最大测试线程数
        self.max_workers = self.config.get('max_workers', 5)
        
        # 是否检查匿名性
        self.check_anonymity = self.config.get('check_anonymity', True)
        
        # 是否尝试弱密码
        self.try_passwords = self.config.get('try_passwords', True)
        
        # 初始化密码尝试器
        self.password_tester = PasswordTester(self.config.get('password_tester', {}))
        
    def check(self, ip: str, port: int) -> Dict[str, Dict[str, Any]]:
        """
        检查一个IP端口是否是可用的代理
        
        Args:
            ip: IP地址
            port: 端口号
            
        Returns:
            dict: 检查结果，按协议分类，如 {'http': {'is_valid': True, ...}, 'socks5': {...}}
        """
        results = {}
        
        # 检查HTTP代理
        http_result = self.check_http_proxy(ip, port)
        if http_result.get('is_valid', False):
            results['http'] = http_result
            
        # 检查HTTPS代理
        https_result = self.check_https_proxy(ip, port)
        if https_result.get('is_valid', False):
            results['https'] = https_result
            
        # 检查Socks5代理
        socks5_result = self.check_socks_proxy(ip, port, proxy_type='socks5')
        if socks5_result.get('is_valid', False):
            results['socks5'] = socks5_result
            
        # 检查Socks4代理
        socks4_result = self.check_socks_proxy(ip, port, proxy_type='socks4')
        if socks4_result.get('is_valid', False):
            results['socks4'] = socks4_result
            
        return results
        
    def check_proxy(self, ip: str, port: int, protocol: str) -> Dict[str, Any]:
        """
        检查特定协议的代理
        
        Args:
            ip: IP地址
            port: 端口号
            protocol: 协议类型，如http、https、socks4、socks5
            
        Returns:
            dict: 检查结果
        """
        if protocol == 'http':
            return self.check_http_proxy(ip, port)
        elif protocol == 'https':
            return self.check_https_proxy(ip, port)
        elif protocol == 'socks4':
            return self.check_socks_proxy(ip, port, proxy_type='socks4')
        elif protocol == 'socks5':
            return self.check_socks_proxy(ip, port, proxy_type='socks5')
        else:
            return {'is_valid': False, 'error': f"不支持的协议: {protocol}"}
            
    def check_http_proxy(self, ip: str, port: int) -> Dict[str, Any]:
        """
        检查HTTP代理
        
        Args:
            ip: IP地址
            port: 端口号
            
        Returns:
            dict: 检查结果
        """
        try:
            start_time = time.time()
            
            # 构造代理
            proxy_url = f"http://{ip}:{port}"
            proxies = {
                'http': proxy_url
            }
            
            # 随机选择一个测试URL
            test_url = self.test_urls[0]
            if len(self.test_urls) > 1:
                test_url = self.test_urls[0]  # 使用第一个作为最稳定的
            
            # 发送请求
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; ProxyChecker/1.0)'}
            )
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 检查响应
            if response.status_code == 200 and len(response.text) > 0:
                result = {
                    'is_valid': True,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'content_length': len(response.text)
                }
                
                # 检查匿名性
                if self.check_anonymity:
                    result['is_anonymous'] = self._check_anonymity(proxies, 'http')
                
                # 提取地理位置信息
                geo_info = self._get_geo_info(ip)
                if geo_info:
                    result.update(geo_info)
                
                # 尝试弱密码验证
                if self.try_passwords:
                    credentials = self.password_tester.test(ip, port, 'http')
                    if credentials:
                        result['auth_required'] = True
                        result['username'] = credentials.get('username', '')
                        result['password'] = credentials.get('password', '')
                    else:
                        result['auth_required'] = False
                
                return result
            else:
                return {
                    'is_valid': False,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'error': f"无效的响应: {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"HTTP代理检查失败: {ip}:{port} - {str(e)}")
            return {'is_valid': False, 'error': str(e)}
        except Exception as e:
            logger.debug(f"HTTP代理检查发生异常: {ip}:{port} - {str(e)}")
            return {'is_valid': False, 'error': str(e)}
            
    def check_https_proxy(self, ip: str, port: int) -> Dict[str, Any]:
        """
        检查HTTPS代理
        
        Args:
            ip: IP地址
            port: 端口号
            
        Returns:
            dict: 检查结果
        """
        try:
            start_time = time.time()
            
            # 构造代理
            proxy_url = f"http://{ip}:{port}"
            proxies = {
                'https': proxy_url
            }
            
            # 随机选择一个HTTPS测试URL
            test_url = "https://httpbin.org/ip"
            
            # 发送请求
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; ProxyChecker/1.0)'},
                verify=False  # 禁用SSL验证，可能不够安全
            )
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 检查响应
            if response.status_code == 200 and len(response.text) > 0:
                result = {
                    'is_valid': True,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'content_length': len(response.text),
                    'is_ssl': True
                }
                
                # 检查匿名性
                if self.check_anonymity:
                    result['is_anonymous'] = self._check_anonymity(proxies, 'https')
                
                # 提取地理位置信息
                geo_info = self._get_geo_info(ip)
                if geo_info:
                    result.update(geo_info)
                
                # 尝试弱密码验证
                if self.try_passwords:
                    credentials = self.password_tester.test(ip, port, 'https')
                    if credentials:
                        result['auth_required'] = True
                        result['username'] = credentials.get('username', '')
                        result['password'] = credentials.get('password', '')
                    else:
                        result['auth_required'] = False
                
                return result
            else:
                return {
                    'is_valid': False,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'error': f"无效的响应: {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"HTTPS代理检查失败: {ip}:{port} - {str(e)}")
            return {'is_valid': False, 'error': str(e)}
        except Exception as e:
            logger.debug(f"HTTPS代理检查发生异常: {ip}:{port} - {str(e)}")
            return {'is_valid': False, 'error': str(e)}
            
    def check_socks_proxy(self, ip: str, port: int, proxy_type='socks5') -> Dict[str, Any]:
        """
        检查SOCKS代理
        
        Args:
            ip: IP地址
            port: 端口号
            proxy_type: 代理类型，socks5或socks4
            
        Returns:
            dict: 检查结果
        """
        try:
            # 检查是否安装了socks支持
            try:
                import socks
            except ImportError:
                logger.warning("未安装PySocks，无法检查SOCKS代理")
                return {'is_valid': False, 'error': "未安装PySocks"}
                
            start_time = time.time()
            
            # 构造代理
            proxy_url = f"{proxy_type}://{ip}:{port}"
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 随机选择一个测试URL
            test_url = "http://httpbin.org/ip"
            
            # 发送请求
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; ProxyChecker/1.0)'}
            )
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 检查响应
            if response.status_code == 200 and len(response.text) > 0:
                result = {
                    'is_valid': True,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'content_length': len(response.text)
                }
                
                # 检查匿名性
                if self.check_anonymity:
                    result['is_anonymous'] = self._check_anonymity(proxies, 'http')
                
                # 提取地理位置信息
                geo_info = self._get_geo_info(ip)
                if geo_info:
                    result.update(geo_info)
                    
                # 尝试弱密码验证
                if self.try_passwords:
                    credentials = self.password_tester.test(ip, port, proxy_type)
                    if credentials:
                        result['auth_required'] = True
                        result['username'] = credentials.get('username', '')
                        result['password'] = credentials.get('password', '')
                    else:
                        result['auth_required'] = False
                
                return result
            else:
                return {
                    'is_valid': False,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'error': f"无效的响应: {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"{proxy_type.upper()}代理检查失败: {ip}:{port} - {str(e)}")
            return {'is_valid': False, 'error': str(e)}
        except Exception as e:
            logger.debug(f"{proxy_type.upper()}代理检查发生异常: {ip}:{port} - {str(e)}")
            return {'is_valid': False, 'error': str(e)}
            
    def _check_anonymity(self, proxies: Dict[str, str], protocol: str) -> bool:
        """
        检查代理匿名性
        
        Args:
            proxies: 代理配置
            protocol: 协议（http或https）
            
        Returns:
            bool: 是否匿名
        """
        try:
            # 请求可以显示原始IP的网站
            url = "http://httpbin.org/headers"
            
            # 发送请求
            response = requests.get(
                url,
                proxies=proxies,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; ProxyChecker/1.0)'}
            )
            
            # 解析响应
            if response.status_code == 200:
                headers = response.json().get('headers', {})
                
                # 检查是否存在泄露真实IP的头部
                for header in ['X-Forwarded-For', 'Via', 'X-Real-IP']:
                    if header in headers:
                        return False
                        
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"检查代理匿名性失败: {str(e)}")
            return False
            
    def _get_geo_info(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        获取IP地理位置信息
        
        Args:
            ip: IP地址
            
        Returns:
            dict: 地理位置信息，如果失败则返回None
        """
        try:
            # 使用免费API获取地理位置
            response = requests.get(
                f"https://ipinfo.io/{ip}/json",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'country': data.get('country'),
                    'country_name': data.get('country'),  # 需要另一个API获取完整国家名称
                    'region': data.get('region'),
                    'city': data.get('city')
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"获取IP地理位置信息失败: {str(e)}")
            return None 