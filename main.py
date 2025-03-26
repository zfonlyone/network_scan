#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理IP扫描器主程序
"""

import os
import logging
import argparse
from database.connection import init_db
from utils.config import load_config
from utils.logging import setup_logging
from utils.backup import DatabaseBackup
from scanner.scanner_manager import ScannerManager
from api.app import create_app

logger = logging.getLogger(__name__)


def main():
    """主程序入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='代理IP扫描器')
    parser.add_argument('--config', default='config/production.yml', help='配置文件路径')
    parser.add_argument('--mode', choices=['scanner', 'api', 'all'], default='all', help='运行模式')
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        print(f"无法加载配置文件: {args.config}")
        return
    
    # 配置日志
    setup_logging(config.get('logging', {}))
    
    # 数据库初始化
    logger.info("初始化数据库连接")
    init_db(config.get('database', {}))
    
    # 初始化数据库备份
    backup_manager = None
    if 'backup' in config:
        logger.info("初始化数据库备份管理器")
        backup_manager = DatabaseBackup(config.get('backup', {}))
        backup_manager.start_scheduler()
    
    # 根据模式启动相应组件
    if args.mode in ['scanner', 'all']:
        # 启动扫描器
        logger.info("启动扫描器")
        scanner_manager = ScannerManager(config.get('scanner', {}))
        scanner_manager.start()
    
    if args.mode in ['api', 'all']:
        # 启动API服务
        logger.info("启动API服务")
        app = create_app(config.get('api', {}))
        host = config.get('api', {}).get('host', '0.0.0.0')
        port = config.get('api', {}).get('port', 5000)
        app.run(host=host, port=port)
    
    # 注册退出处理
    def cleanup():
        logger.info("程序退出，清理资源")
        if args.mode in ['scanner', 'all']:
            scanner_manager.stop()
        if backup_manager:
            backup_manager.stop_scheduler()
    
    # 捕获键盘中断
    try:
        # 如果只运行扫描器，阻塞主线程
        if args.mode == 'scanner':
            import time
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("收到中断信号，程序退出")
        cleanup()


if __name__ == "__main__":
    main()