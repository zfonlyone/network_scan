# 代理IP扫描器

一个自动化的代理IP扫描、验证和管理系统，用于发现可用的代理IP并提供API服务。

## 项目概述

该项目旨在构建一个完整的代理IP扫描和管理系统，可以自动扫描目标IP地址范围的常用代理端口，验证代理的可用性和匿名性，并将可用的代理IP添加到代理池中。系统通过API提供代理IP服务，支持各种筛选条件。

### 主要功能

- 自动扫描代理IP的常用端口
- 验证代理连接和匿名性
- 尝试使用弱密码连接验证
- 管理代理IP池，定期验证代理可用性
- 提供REST API接口获取代理IP
- 支持基于响应时间、地理位置等条件筛选代理
- 多种安全认证方式：API密钥、IP白名单、JWT、请求限速

## 技术栈

- **后端**: Python 3.9+
- **Web框架**: Flask
- **数据库**: MySQL
- **缓存**: Redis
- **容器化**: Docker & Docker Compose
- **扫描工具**: Nmap, Masscan
- **代理验证**: 自定义验证脚本

## 系统架构

系统由以下几个主要组件构成：

1. **扫描引擎**: 负责扫描目标IP的端口开放情况和尝试弱密码连接
2. **IP管理模块**: 管理扫描到的可用代理IP
3. **数据库**: 存储扫描结果和可用代理IP信息
4. **Redis缓存**: 维护活跃代理IP池，提高访问效率
5. **API服务**: 提供REST API接口，允许外部程序获取代理IP
6. **备份系统**: 自动备份数据库，支持定时备份和恢复

## 快速开始

### 环境要求

- VPS服务器（建议配置：1核CPU，1GB内存，15GB存储空间）
- Docker和Docker Compose
- Linux操作系统（Ubuntu/Debian推荐）

### 安装步骤

1. 克隆代码库:
```bash
git clone https://github.com/yourusername/network_scan.git
cd network_scan
```

2. 创建并配置敏感文件:
```bash
# 复制配置文件示例并进行配置
cp config/production.yml.example config/production.yml
# 编辑配置文件，修改敏感信息
nano config/production.yml

# 复制字典文件示例
cp dict/usernames.txt.example dict/usernames.txt
cp dict/passwords.txt.example dict/passwords.txt
# 根据需要编辑字典文件
```

3. 构建并启动服务:
```bash
docker-compose up -d
```

4. 检查服务状态:
```bash
docker-compose ps
```

5. 查看日志:
```bash
docker-compose logs -f
```

## 配置详解

### 主要配置文件

系统的主要配置文件位于`config`目录：

- `production.yml`: 生产环境配置文件（从示例文件创建）

### 配置项说明

#### 1. 安全认证配置

系统支持多种安全认证方式，可以在配置文件中启用/禁用：

```yaml
api:
  # API密钥配置
  api_key: "your_secret_api_key"  # 主API密钥
  api_keys:                        # 额外支持的API密钥列表
    - "api_key_1"
    - "api_key_2"
  hmac_secret: "your_hmac_secret"  # HMAC签名验证密钥
  
  # IP白名单配置
  ip_whitelist_enabled: false      # 是否启用IP白名单
  ip_whitelist:                    # IP白名单列表
    - "127.0.0.1"
    - "10.0.0.0/8"                 # 支持CIDR格式
    
  # JWT认证配置
  jwt_auth_enabled: false          # 是否启用JWT认证
  jwt_secret: "your_jwt_secret"    # JWT密钥
  jwt_expire_seconds: 3600         # JWT过期时间（秒）
  
  # 速率限制配置
  rate_limit_enabled: true         # 是否启用速率限制
  rate_limit: 100                  # 每分钟最大请求数
  rate_limit_period: 60            # 时间窗口(秒)
```

#### 2. 扫描器配置

配置扫描引擎的行为：

```yaml
scanner:
  threads: 200                     # 扫描线程数
  timeout: 5                       # 连接超时(秒)
  scan_interval: 300               # 扫描间隔(秒)
  verify_threads: 50               # 验证线程数
  verify_timeout: 10               # 验证超时(秒)
  verify_interval: 600             # 验证间隔(秒)
```

#### 3. 弱密码测试配置

配置弱密码测试功能：

```yaml
scanner:
  password_test:
    enabled: true                  # 是否启用弱密码测试
    max_tries: 5                   # 最大尝试次数
    username_file: "dict/usernames.txt"  # 用户名字典文件
    password_file: "dict/passwords.txt"  # 密码字典文件
```

#### 4. 数据库和Redis配置

数据库配置：

```yaml
database:
  type: mysql
  host: db
  port: 3306
  username: your_db_username
  password: your_db_password
  database: proxy_scanner
```

Redis配置：

```yaml
redis:
  host: redis
  port: 6379
  db: 0
  password: your_redis_password
```

### 敏感文件处理

系统使用以下策略处理敏感文件：

1. `.gitignore` 文件用于排除敏感文件（配置文件、密钥、证书等）
2. 所有敏感配置文件都提供了`.example`示例文件
3. 数据库和字典文件默认不包含在版本控制中

敏感文件列表：
- `config/production.yml`: 生产环境配置，包含API密钥和数据库凭据
- `dict/usernames.txt` 和 `dict/passwords.txt`: 弱密码测试字典文件
- `data/`: 数据目录，包含数据库文件和GeoIP数据库
- `logs/`: 日志目录

## API使用指南

系统提供RESTful API接口，用于获取和管理代理IP。

### 认证方式

API支持多种认证方式：

1. **API密钥认证**
```bash
# 通过请求头
curl -H "X-API-Key: your_api_key" "http://your-server:8000/api/v1/proxies"

# 通过URL参数
curl "http://your-server:8000/api/v1/proxies?api_key=your_api_key"
```

2. **HMAC签名认证**
```bash
# 需要额外提供时间戳
curl -H "X-API-Key: key_id:signature" -H "X-Timestamp: 1649856000" "http://your-server:8000/api/v1/proxies"
```

3. **JWT令牌认证**
```bash
# 首先获取JWT令牌
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  "http://your-server:8000/api/v1/auth/token"

# 使用JWT令牌访问API
curl -H "Authorization: Bearer your_jwt_token" "http://your-server:8000/api/v1/proxies"
```

### 主要API端点

#### 获取代理列表

```bash
# 获取代理列表
curl -H "X-API-Key: your_api_key" "http://your-server:8000/api/v1/proxies?limit=10&type=http&anonymity=high_anonymous"
```

支持的筛选参数：
- `country`: 国家/地区代码
- `type`: 代理类型 (http/https/socks4/socks5)
- `anonymity`: 匿名级别 (transparent/anonymous/high_anonymous)
- `limit`: 返回结果数量限制
- `page`: 分页页码
- `sort_by`: 排序字段
- `sort_order`: 排序方向 (asc/desc)
- `min_score`: 最小评分
- `active_within`: 最近活跃时间（小时）
- `export`: 导出格式 (json/csv/txt)

#### 获取随机代理

```bash
# 获取随机代理
curl -H "X-API-Key: your_api_key" "http://your-server:8000/api/v1/proxies/random?type=socks5"
```

#### 验证代理

```bash
# 验证外部代理
curl -X POST -H "X-API-Key: your_api_key" -H "Content-Type: application/json" \
  -d '{"proxy":"1.2.3.4:8080","type":"http"}' \
  "http://your-server:8000/api/v1/proxies/verify"
```

#### 报告代理状态

```bash
# 报告代理状态
curl -X POST -H "X-API-Key: your_api_key" -H "Content-Type: application/json" \
  -d '{"proxy_id":123,"status":"success","details":{"response_time":0.5}}' \
  "http://your-server:8000/api/v1/proxies/report"
```

#### 获取系统状态

```bash
# 获取系统状态
curl -H "X-API-Key: your_api_key" "http://your-server:8000/api/v1/system/status"
```

详细的API文档可以在 [API文档](docs/api.md) 中查看。

## 数据库备份与恢复

系统支持自动备份MySQL数据库，备份文件保存在`backup/`目录。

### 备份特性

- **定时备份**: 默认每24小时自动备份一次
- **备份保留**: 自动清理超过指定天数的旧备份
- **压缩存储**: 备份文件使用gzip压缩，节省存储空间

### 手动备份和恢复

执行手动备份:

```bash
docker exec proxy_scanner_scanner python -m utils.backup --action backup
```

查看可用备份:

```bash
docker exec proxy_scanner_scanner python -m utils.backup --action list
```

从备份恢复:

```bash
docker exec proxy_scanner_scanner python -m utils.backup --action restore --file backup/proxy_scanner_backup_20230327_120000.sql.gz
```

## 故障排除

常见问题及解决方案：

1. **服务无法启动**
   - 检查配置文件格式是否正确
   - 查看日志：`docker-compose logs -f`
   - 确保所有必要的端口未被占用

2. **数据库连接失败**
   - 检查数据库配置是否正确
   - 确保数据库服务运行正常
   - 检查网络连接和防火墙设置

3. **API认证失败**
   - 确认使用了正确的API密钥或JWT令牌
   - 检查IP白名单设置
   - 查看速率限制配置是否过严

## 项目文档

- [详细计划](详细计划.md)
- [执行步骤](执行步骤计划.md)
- [软件开发规范](软件开发规范.md)
- [任务进度](任务进度.md)
- [API文档](docs/api.md)

## 贡献指南

欢迎对项目进行贡献！请遵循以下步骤：

1. Fork本项目
2. 创建您的特性分支：`git checkout -b feature/my-new-feature`
3. 提交您的更改：`git commit -am 'Add some feature'`
4. 将您的更改推送到分支：`git push origin feature/my-new-feature`
5. 提交Pull Request

## 许可证

MIT 