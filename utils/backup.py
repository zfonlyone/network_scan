#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库备份模块

提供PostgreSQL数据库的备份、恢复和管理功能。
支持自动备份、备份压缩、备份验证和清理旧备份等功能。
"""

import os
import sys
import time
import logging
import datetime
import subprocess
import shutil
import glob
import gzip
import threading
from pathlib import Path

from utils.config import load_config

logger = logging.getLogger(__name__)


class DatabaseBackup:
    """数据库备份管理器"""
    
    def __init__(self, config=None):
        """
        初始化数据库备份管理器
        
        Args:
            config: 备份配置字典
        """
        self.config = config or {}
        
        # 从全局配置中获取数据库配置
        if not self.config:
            global_config = load_config()
            self.config = global_config.get('backup', {})
            self.db_config = global_config.get('database', {})
        else:
            self.db_config = self.config.get('database', {})
        
        # 备份目录
        self.backup_dir = self.config.get('backup_dir', 'backups')
        
        # 创建备份目录（如果不存在）
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 备份保留天数
        self.retention_days = self.config.get('retention_days', 7)
        
        # 备份文件前缀
        self.backup_prefix = self.config.get('backup_prefix', 'proxy_scanner_backup')
        
        # 数据库配置
        self.db_host = self.db_config.get('host', 'localhost')
        self.db_port = self.db_config.get('port', 5432)
        self.db_name = self.db_config.get('database', 'proxy_scanner')
        self.db_user = self.db_config.get('username', 'postgres')
        self.db_password = self.db_config.get('password', '')
        
        # 备份锁，防止多个备份同时运行
        self.backup_lock = threading.Lock()
        
        # 备份计划线程
        self.schedule_thread = None
        self.running = False
        
        # 备份间隔（秒），默认24小时
        self.backup_interval = self.config.get('backup_interval', 86400)
    
    def start_scheduler(self):
        """启动备份调度器"""
        if self.running:
            logger.warning("备份调度器已经在运行")
            return
            
        self.running = True
        self.schedule_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
        self.schedule_thread.start()
        logger.info("备份调度器已启动")
    
    def stop_scheduler(self):
        """停止备份调度器"""
        if not self.running:
            logger.warning("备份调度器未运行")
            return
            
        self.running = False
        if self.schedule_thread:
            self.schedule_thread.join(timeout=5)
        logger.info("备份调度器已停止")
    
    def _scheduler_worker(self):
        """备份调度工作线程"""
        logger.info("备份调度工作线程已启动")
        
        # 启动后立即执行一次备份
        if self.config.get('backup_on_start', True):
            self.create_backup()
        
        # 循环执行定时备份
        while self.running:
            time.sleep(self.backup_interval)
            
            if not self.running:
                break
                
            try:
                self.create_backup()
            except Exception as e:
                logger.error(f"定时备份失败: {str(e)}", exc_info=True)
    
    def create_backup(self):
        """
        创建数据库备份
        
        Returns:
            str: 备份文件路径
        """
        # 获取锁，防止多个备份同时运行
        if not self.backup_lock.acquire(blocking=False):
            logger.warning("另一个备份正在进行中")
            return None
        
        try:
            # 生成备份文件名
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f"{self.backup_prefix}_{timestamp}.sql")
            
            logger.info(f"开始备份数据库 {self.db_name} 到 {backup_file}")
            
            # 构建环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password
            
            # 执行pg_dump命令
            cmd = [
                'pg_dump',
                '-h', self.db_host,
                '-p', str(self.db_port),
                '-U', self.db_user,
                '-F', 'p',  # 纯文本格式
                '-b',  # 包括大对象
                '-v',  # 详细输出
                '-f', backup_file,
                self.db_name
            ]
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            # 检查返回值
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8')
                logger.error(f"数据库备份失败: {error_msg}")
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                return None
            
            # 压缩备份文件
            compressed_file = self.compress_backup(backup_file)
            
            # 验证备份
            if not self.verify_backup(compressed_file):
                logger.error(f"备份验证失败: {compressed_file}")
                return None
            
            # 清理旧备份
            self.cleanup_old_backups()
            
            logger.info(f"数据库备份完成: {compressed_file}")
            return compressed_file
            
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}", exc_info=True)
            return None
        finally:
            # 释放锁
            self.backup_lock.release()
    
    def compress_backup(self, backup_file):
        """
        压缩备份文件
        
        Args:
            backup_file: 备份文件路径
            
        Returns:
            str: 压缩后的文件路径
        """
        compressed_file = f"{backup_file}.gz"
        logger.info(f"压缩备份文件: {backup_file} -> {compressed_file}")
        
        try:
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除原始文件
            os.remove(backup_file)
            
            return compressed_file
        except Exception as e:
            logger.error(f"压缩备份文件失败: {str(e)}", exc_info=True)
            return backup_file
    
    def verify_backup(self, backup_file):
        """
        验证备份文件
        
        Args:
            backup_file: 备份文件路径
            
        Returns:
            bool: 验证是否成功
        """
        logger.info(f"验证备份文件: {backup_file}")
        
        # 如果文件不存在或大小为0，验证失败
        if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
            logger.error(f"备份文件不存在或为空: {backup_file}")
            return False
        
        # 如果是压缩文件，尝试读取验证
        if backup_file.endswith('.gz'):
            try:
                with gzip.open(backup_file, 'rb') as f:
                    # 读取前1024字节验证文件格式
                    data = f.read(1024)
                    if not data:
                        logger.error(f"备份文件为空: {backup_file}")
                        return False
                return True
            except Exception as e:
                logger.error(f"验证备份文件失败: {str(e)}")
                return False
        
        return True
    
    def cleanup_old_backups(self):
        """清理旧备份文件"""
        logger.info(f"清理旧备份文件 (保留 {self.retention_days} 天)")
        
        # 计算截止时间
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.retention_days)
        
        # 查找所有备份文件
        backup_pattern = os.path.join(self.backup_dir, f"{self.backup_prefix}_*.sql*")
        backup_files = glob.glob(backup_pattern)
        
        for backup_file in backup_files:
            file_stat = os.stat(backup_file)
            file_date = datetime.datetime.fromtimestamp(file_stat.st_mtime)
            
            # 如果文件早于截止日期，则删除
            if file_date < cutoff_date:
                logger.info(f"删除旧备份文件: {backup_file}")
                try:
                    os.remove(backup_file)
                except Exception as e:
                    logger.error(f"删除备份文件失败: {str(e)}")
    
    def restore_backup(self, backup_file):
        """
        从备份文件恢复数据库
        
        Args:
            backup_file: 备份文件路径
            
        Returns:
            bool: 恢复是否成功
        """
        logger.info(f"从备份文件恢复数据库: {backup_file}")
        
        # 获取锁，防止备份和恢复同时进行
        if not self.backup_lock.acquire(blocking=False):
            logger.warning("备份正在进行中，无法恢复")
            return False
        
        try:
            # 检查文件是否存在
            if not os.path.exists(backup_file):
                logger.error(f"备份文件不存在: {backup_file}")
                return False
            
            # 如果是压缩文件，先解压
            if backup_file.endswith('.gz'):
                uncompressed_file = backup_file[:-3]  # 移除.gz后缀
                try:
                    with gzip.open(backup_file, 'rb') as f_in:
                        with open(uncompressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    backup_file = uncompressed_file
                except Exception as e:
                    logger.error(f"解压备份文件失败: {str(e)}", exc_info=True)
                    return False
            
            # 构建环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password
            
            # 执行psql命令恢复
            cmd = [
                'psql',
                '-h', self.db_host,
                '-p', str(self.db_port),
                '-U', self.db_user,
                '-d', self.db_name,
                '-f', backup_file
            ]
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            # 检查返回值
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8')
                logger.error(f"数据库恢复失败: {error_msg}")
                return False
            
            logger.info(f"数据库恢复完成: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"恢复备份失败: {str(e)}", exc_info=True)
            return False
        finally:
            # 释放锁
            self.backup_lock.release()
            
            # 如果解压了临时文件，删除它
            if backup_file.endswith('.sql') and os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                except:
                    pass
    
    def list_backups(self):
        """
        列出所有备份文件
        
        Returns:
            list: 备份文件信息列表
        """
        logger.info("列出所有备份文件")
        
        # 查找所有备份文件
        backup_pattern = os.path.join(self.backup_dir, f"{self.backup_prefix}_*.sql*")
        backup_files = glob.glob(backup_pattern)
        
        # 收集备份文件信息
        backup_info = []
        for backup_file in backup_files:
            file_stat = os.stat(backup_file)
            file_size = file_stat.st_size
            file_date = datetime.datetime.fromtimestamp(file_stat.st_mtime)
            
            backup_info.append({
                'file_path': backup_file,
                'file_name': os.path.basename(backup_file),
                'file_size': file_size,
                'file_date': file_date,
                'compressed': backup_file.endswith('.gz')
            })
        
        # 按日期排序，最新的在前
        backup_info.sort(key=lambda x: x['file_date'], reverse=True)
        
        return backup_info


# 如果作为脚本执行，执行备份
if __name__ == "__main__":
    import argparse
    from utils.logging import setup_logging
    
    # 配置日志
    setup_logging()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='数据库备份工具')
    parser.add_argument('--action', choices=['backup', 'restore', 'list'], default='backup', help='执行操作: backup, restore, list')
    parser.add_argument('--file', help='恢复操作的备份文件')
    args = parser.parse_args()
    
    # 创建备份管理器
    backup_manager = DatabaseBackup()
    
    # 执行操作
    if args.action == 'backup':
        backup_file = backup_manager.create_backup()
        if backup_file:
            print(f"备份成功: {backup_file}")
        else:
            print("备份失败")
            sys.exit(1)
    
    elif args.action == 'restore':
        if not args.file:
            print("恢复操作需要指定备份文件")
            sys.exit(1)
        
        success = backup_manager.restore_backup(args.file)
        if success:
            print(f"恢复成功: {args.file}")
        else:
            print("恢复失败")
            sys.exit(1)
    
    elif args.action == 'list':
        backups = backup_manager.list_backups()
        if not backups:
            print("没有找到备份文件")
        else:
            print("备份文件列表:")
            for backup in backups:
                size_mb = backup['file_size'] / (1024 * 1024)
                print(f"{backup['file_name']} - {backup['file_date']} ({size_mb:.2f}MB)") 