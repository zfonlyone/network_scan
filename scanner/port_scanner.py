#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
端口扫描器模块
"""

import logging
import socket
import subprocess
import tempfile
import os
import time
import random
from typing import List

logger = logging.getLogger(__name__)


class PortScanner:
    """端口扫描器"""
    
    def __init__(self, config=None):
        """
        初始化端口扫描器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 默认扫描端口列表（常见代理端口）
        self.default_ports = self.config.get('ports', [
            80, 443, 808, 1080, 3128, 5555,
            3129, 8000, 8080, 8081, 8888,
            9000, 9090, 6666, 8118, 41258
        ])
        
        # 超时设置
        self.timeout = self.config.get('timeout', 2)
        
        # 扫描方式 (socket, nmap, masscan)
        self.scan_method = self.config.get('method', 'socket')
        
        # 命令行路径
        self.nmap_path = self.config.get('nmap_path', 'nmap')
        self.masscan_path = self.config.get('masscan_path', 'masscan')
        
        # 扫描器速率
        self.rate = self.config.get('rate', 100)
        
    def scan(self, ip: str, ports: List[int] = None) -> List[int]:
        """
        扫描IP的开放端口
        
        Args:
            ip: 目标IP
            ports: 端口列表，不指定则使用默认端口
            
        Returns:
            list: 开放的端口列表
        """
        if ports is None:
            ports = self.default_ports
            
        try:
            # 根据扫描方法选择扫描方式
            if self.scan_method == 'nmap':
                return self._scan_with_nmap(ip, ports)
            elif self.scan_method == 'masscan':
                return self._scan_with_masscan(ip, ports)
            else:
                return self._scan_with_socket(ip, ports)
        except Exception as e:
            logger.error(f"扫描端口失败: {str(e)}")
            return []
            
    def _scan_with_socket(self, ip: str, ports: List[int]) -> List[int]:
        """
        使用Socket扫描端口
        
        Args:
            ip: 目标IP
            ports: 端口列表
            
        Returns:
            list: 开放的端口列表
        """
        open_ports = []
        
        # 随机打乱端口顺序，避免顺序扫描
        random_ports = ports.copy()
        random.shuffle(random_ports)
        
        for port in random_ports:
            try:
                # 创建套接字
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                
                # 尝试连接
                result = sock.connect_ex((ip, port))
                
                if result == 0:
                    # 端口开放
                    open_ports.append(port)
                    logger.debug(f"端口开放: {ip}:{port}")
                
                # 关闭套接字
                sock.close()
                
                # 随机延迟，避免触发防护
                time.sleep(random.uniform(0.1, 0.3))
                
            except Exception as e:
                logger.debug(f"扫描端口 {ip}:{port} 异常: {str(e)}")
        
        return open_ports
        
    def _scan_with_nmap(self, ip: str, ports: List[int]) -> List[int]:
        """
        使用Nmap扫描端口
        
        Args:
            ip: 目标IP
            ports: 端口列表
            
        Returns:
            list: 开放的端口列表
        """
        open_ports = []
        
        try:
            # 构建端口参数
            ports_str = ','.join(map(str, ports))
            
            # 构建命令
            cmd = [
                self.nmap_path,
                '-sS',  # SYN扫描
                '-Pn',  # 跳过主机发现
                '--open',  # 只显示开放端口
                '-T4',  # 扫描速度
                '-n',  # 不进行DNS解析
                '--host-timeout', '30s',
                '-p', ports_str,
                ip
            ]
            
            # 执行命令
            logger.debug(f"执行命令: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Nmap扫描失败: {stderr}")
                return []
                
            # 解析结果
            for line in stdout.split('\n'):
                # 查找端口行
                if 'open' in line and 'tcp' in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        port_info = parts[0]
                        port = int(port_info.split('/')[0])
                        open_ports.append(port)
            
        except Exception as e:
            logger.error(f"Nmap扫描异常: {str(e)}")
        
        return open_ports
        
    def _scan_with_masscan(self, ip: str, ports: List[int]) -> List[int]:
        """
        使用Masscan扫描端口
        
        Args:
            ip: 目标IP
            ports: 端口列表
            
        Returns:
            list: 开放的端口列表
        """
        open_ports = []
        
        try:
            # 创建临时文件保存结果
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_filename = temp_file.name
                
            # 构建端口参数
            ports_str = ','.join(map(str, ports))
            
            # 构建命令
            cmd = [
                self.masscan_path,
                ip,
                '-p', ports_str,
                '--rate', str(self.rate),
                '-oL', temp_filename
            ]
            
            # 执行命令
            logger.debug(f"执行命令: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            # 读取结果文件
            if os.path.exists(temp_filename):
                with open(temp_filename, 'r') as f:
                    for line in f:
                        if line.startswith('#'):
                            continue
                        parts = line.strip().split()
                        if len(parts) >= 3 and parts[0] == 'open':
                            port = int(parts[2])
                            open_ports.append(port)
                
                # 删除临时文件
                os.unlink(temp_filename)
            
        except Exception as e:
            logger.error(f"Masscan扫描异常: {str(e)}")
            
            # 清理临时文件
            if 'temp_filename' in locals() and os.path.exists(temp_filename):
                os.unlink(temp_filename)
        
        return open_ports 