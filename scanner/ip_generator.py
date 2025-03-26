#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IP地址生成器模块
"""

import logging
import random
import ipaddress
from typing import List

logger = logging.getLogger(__name__)


class IPGenerator:
    """IP地址生成器"""
    
    def __init__(self):
        """初始化IP生成器"""
        pass
        
    def generate(self, ip_range: str, limit: int = None) -> List[str]:
        """
        生成IP地址列表
        
        Args:
            ip_range: IP范围（CIDR格式，如"192.168.1.0/24"或单个IP）
            limit: 最大生成数量，默认生成所有
            
        Returns:
            list: IP地址列表
        """
        try:
            # 处理特殊格式
            if '-' in ip_range:
                return self._generate_from_range(ip_range, limit)
            
            # 处理CIDR格式
            network = ipaddress.ip_network(ip_range, strict=False)
            ip_list = list(map(str, network.hosts()))
            
            # 随机排序
            random.shuffle(ip_list)
            
            # 限制数量
            if limit and len(ip_list) > limit:
                ip_list = ip_list[:limit]
                
            return ip_list
            
        except Exception as e:
            logger.error(f"生成IP列表失败: {str(e)}")
            return []
            
    def _generate_from_range(self, ip_range: str, limit: int = None) -> List[str]:
        """
        从范围格式生成IP地址（如"192.168.1.1-192.168.1.100"）
        
        Args:
            ip_range: IP范围
            limit: 最大生成数量
            
        Returns:
            list: IP地址列表
        """
        try:
            # 分割起止IP
            start_ip, end_ip = ip_range.split('-')
            start_ip = start_ip.strip()
            end_ip = end_ip.strip()
            
            # 转换为整数
            start_int = int(ipaddress.IPv4Address(start_ip))
            end_int = int(ipaddress.IPv4Address(end_ip))
            
            # 确保起始IP小于结束IP
            if start_int > end_int:
                start_int, end_int = end_int, start_int
                
            # 生成IP列表
            ip_count = end_int - start_int + 1
            
            if limit and ip_count > limit:
                # 随机选择子集
                selected_ints = random.sample(range(start_int, end_int + 1), limit)
                ip_list = [str(ipaddress.IPv4Address(ip_int)) for ip_int in selected_ints]
            else:
                # 生成所有IP
                ip_list = [str(ipaddress.IPv4Address(start_int + i)) for i in range(ip_count)]
                # 随机排序
                random.shuffle(ip_list)
                
            return ip_list
            
        except Exception as e:
            logger.error(f"从范围生成IP列表失败: {str(e)}")
            return []
            
    def generate_random(self, count: int = 100) -> List[str]:
        """
        生成随机IP地址列表
        
        Args:
            count: 生成数量
            
        Returns:
            list: IP地址列表
        """
        ip_list = []
        for _ in range(count):
            # 生成随机IP
            ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            ip_list.append(ip)
            
        return ip_list 