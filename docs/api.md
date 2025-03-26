# 代理IP扫描器 API 文档

本文档详细介绍了代理IP扫描器的API接口，包括接口功能、请求方式、参数说明和响应示例。

## API概述

代理IP扫描器提供了REST风格的API接口，允许用户获取可用的代理IP信息、随机代理和系统统计数据。所有接口均返回JSON格式数据。

## 接口认证

所有API接口都需要认证才能访问。认证方式有两种：

1. **请求头认证**：在HTTP请求头中添加`X-API-Key`字段
2. **查询参数认证**：在URL参数中添加`api_key`参数

API密钥可以在系统配置文件中设置或通过环境变量`API_KEY`提供。

认证失败时，API将返回401状态码和错误信息。

### 认证示例

```bash
# 请求头认证
curl -H "X-API-Key: your_api_key_here" "http://your-server.com:5000/api/proxies"

# 查询参数认证
curl "http://your-server.com:5000/api/proxies?api_key=your_api_key_here"
```

## 接口列表

| 接口 | 方法 | 描述 |
|------|------|------|
| `/proxies` | GET | 获取代理列表 |
| `/proxies/random` | GET | 获取随机代理 |
| `/proxies/{proxy_id}` | GET | 获取指定ID的代理 |
| `/stats` | GET | 获取系统统计信息 |

## 接口详情

### 1. 获取代理列表

获取符合条件的代理IP列表。

**请求方法**：GET

**URL**：`/proxies`

**参数说明**：

| 参数 | 类型 | 必选 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 10 | 返回结果数量限制，最大100 |
| offset | int | 否 | 0 | 分页偏移量 |
| protocol | string | 否 | - | 代理协议过滤，可选值：http, https, socks4, socks5 |
| is_valid | bool | 否 | true | 是否只返回有效代理 |
| anonymous | bool | 否 | - | 是否只返回匿名代理 |
| country | string | 否 | - | 国家代码过滤（两位字母，如: US, CN） |
| max_response_time | float | 否 | - | 最大响应时间过滤（秒） |
| min_success_ratio | float | 否 | - | 最小成功率过滤（0-1） |
| order_by | string | 否 | - | 排序方式，可选值：response_time, success_ratio, last_checked |

**请求示例**：

```bash
curl -H "X-API-Key: your_api_key_here" "http://your-server.com:5000/api/proxies?limit=5&protocol=https&country=US&anonymous=true"
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "total": 47,
    "count": 5,
    "offset": 0,
    "limit": 5,
    "proxies": [
      {
        "id": 42,
        "ip": "192.168.1.1",
        "port": 8080,
        "protocol": "https",
        "username": "user",
        "password": "pass",
        "country": "US",
        "country_name": "United States",
        "region": "California",
        "city": "Los Angeles",
        "is_anonymous": true,
        "is_ssl": true,
        "is_valid": true,
        "response_time": 0.75,
        "success_count": 45,
        "fail_count": 5,
        "success_ratio": 0.9,
        "last_checked": "2023-03-27T08:15:30.000Z",
        "last_successful": "2023-03-27T08:15:30.000Z",
        "created_at": "2023-03-26T10:00:00.000Z",
        "updated_at": "2023-03-27T08:15:30.000Z"
      },
      // ... 其他代理
    ]
  }
}
```

### 2. 获取随机代理

获取符合条件的随机代理IP。

**请求方法**：GET

**URL**：`/proxies/random`

**参数说明**：

| 参数 | 类型 | 必选 | 默认值 | 说明 |
|------|------|------|--------|------|
| protocol | string | 否 | - | 代理协议过滤，可选值：http, https, socks4, socks5 |
| is_valid | bool | 否 | true | 是否只返回有效代理 |
| anonymous | bool | 否 | - | 是否只返回匿名代理 |
| country | string | 否 | - | 国家代码过滤（两位字母，如: US, CN） |

**请求示例**：

```bash
curl -H "X-API-Key: your_api_key_here" "http://your-server.com:5000/api/proxies/random?protocol=socks5"
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "id": 123,
    "ip": "203.0.113.1",
    "port": 1080,
    "protocol": "socks5",
    "username": null,
    "password": null,
    "country": "JP",
    "country_name": "Japan",
    "region": "Tokyo",
    "city": "Tokyo",
    "is_anonymous": true,
    "is_ssl": false,
    "is_valid": true,
    "response_time": 0.35,
    "success_count": 78,
    "fail_count": 2,
    "success_ratio": 0.975,
    "last_checked": "2023-03-27T09:22:15.000Z",
    "last_successful": "2023-03-27T09:22:15.000Z",
    "created_at": "2023-03-26T15:30:00.000Z",
    "updated_at": "2023-03-27T09:22:15.000Z"
  }
}
```

### 3. 获取指定ID的代理

通过ID获取特定代理的详细信息。

**请求方法**：GET

**URL**：`/proxies/{proxy_id}`

**参数说明**：

| 参数 | 类型 | 必选 | 默认值 | 说明 |
|------|------|------|--------|------|
| proxy_id | int | 是 | - | 代理ID |

**请求示例**：

```bash
curl -H "X-API-Key: your_api_key_here" "http://your-server.com:5000/api/proxies/123"
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "id": 123,
    "ip": "203.0.113.1",
    "port": 1080,
    "protocol": "socks5",
    "username": null,
    "password": null,
    "country": "JP",
    "country_name": "Japan",
    "region": "Tokyo",
    "city": "Tokyo",
    "is_anonymous": true,
    "is_ssl": false,
    "is_valid": true,
    "response_time": 0.35,
    "success_count": 78,
    "fail_count": 2,
    "success_ratio": 0.975,
    "last_checked": "2023-03-27T09:22:15.000Z",
    "last_successful": "2023-03-27T09:22:15.000Z",
    "created_at": "2023-03-26T15:30:00.000Z",
    "updated_at": "2023-03-27T09:22:15.000Z"
  }
}
```

### 4. 获取系统统计信息

获取系统中代理IP的统计信息。

**请求方法**：GET

**URL**：`/stats`

**参数说明**：无

**请求示例**：

```bash
curl -H "X-API-Key: your_api_key_here" "http://your-server.com:5000/api/stats"
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "proxies": {
      "total": 5487,
      "valid": 3926,
      "by_protocol": {
        "http": 1548,
        "https": 1235,
        "socks4": 523,
        "socks5": 620
      },
      "anonymous": 2105
    },
    "targets": {
      "total": 15
    }
  }
}
```

## 错误码说明

| 状态码 | 错误代码 | 描述 |
|--------|----------|------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 认证失败 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器内部错误 |

**错误响应示例**：

```json
{
  "success": false,
  "error": "Unauthorized",
  "message": "API密钥无效"
}
```

## 使用示例

### Python示例

```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "http://your-server.com:5000/api"

headers = {
    "X-API-Key": API_KEY
}

# 获取HTTP匿名代理列表
response = requests.get(
    f"{BASE_URL}/proxies",
    headers=headers,
    params={
        "protocol": "http",
        "anonymous": "true",
        "limit": 10
    }
)

if response.status_code == 200:
    data = response.json()
    proxies = data["data"]["proxies"]
    for proxy in proxies:
        print(f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}")
else:
    print(f"Error: {response.status_code}")
    print(response.json())

# 获取随机SOCKS5代理
response = requests.get(
    f"{BASE_URL}/proxies/random",
    headers=headers,
    params={"protocol": "socks5"}
)

if response.status_code == 200:
    proxy = response.json()["data"]
    print(f"Random proxy: {proxy['protocol']}://{proxy['ip']}:{proxy['port']}")
```

### Node.js示例

```javascript
const axios = require('axios');

const API_KEY = 'your_api_key_here';
const BASE_URL = 'http://your-server.com:5000/api';

// 获取响应时间低于1秒的HTTPS代理
axios.get(`${BASE_URL}/proxies`, {
  headers: {
    'X-API-Key': API_KEY
  },
  params: {
    protocol: 'https',
    max_response_time: 1.0,
    limit: 5
  }
})
.then(response => {
  const proxies = response.data.data.proxies;
  proxies.forEach(proxy => {
    console.log(`${proxy.protocol}://${proxy.ip}:${proxy.port} - ${proxy.response_time}s`);
  });
})
.catch(error => {
  console.error('Error:', error.response ? error.response.data : error.message);
});
```

## 注意事项

1. API接口有请求速率限制，请合理使用
2. 代理IP可能随时变化，请妥善处理连接失败的情况
3. 密码信息仅会在使用API密钥认证的情况下返回
4. 建议在使用代理前先进行可用性验证 