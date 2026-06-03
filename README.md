# RS485 Modbus Concrete Sensor Monitor

基于 `Python + Django + Django Ninja` 的混凝土传感器实时监测系统。

---

## 1. 当前状态

### 已完成

- Django 项目结构 + Django Ninja API
- 工控风格监控首页（高密度矩阵、多 Tab 指标、10 分钟历史趋势）
- **三档数据源切换**：真实数据 / 网络模拟 / 本地模拟
- **Redis 数据链路**：Django 按数据源读取对应 Redis 命名空间
- **Modbus TCP 采集器**：`collector/` 实现 FC03 读取 + Redis 写入，支持可配置传感器数量
- **网络模拟**：`mock_server --feed` 每秒向 Redis 写入模拟快照，与真实数据命名空间隔离
- **本地模拟降级**：Redis 不可用时自动回退到进程内 mock，无需任何外部依赖
- `test/` 独立测试原型 + 压测脚本

### 未完成

- 真实 Modbus TCP 采集联调（待接硬件）
- 长期历史持久化
- 告警模块

---

## 2. 数据流架构

```
真实数据（生产）：
  RS485 传感器 → python collector/main.py
      ↓ Modbus TCP FC03 解包 → RedisWriter
  Redis:6379  monitor:sensor:{ip}:{sensor_index}   TTL=10s
      ↓ Django RedisReader（真实数据档）
  前端

网络模拟（开发联调）：
  python test/mock_server.py --feed
      ↓ 每秒写 320 key（20 网关 × 16 传感器）TTL=10s
  Redis:6379  monitor:test:{ip}:{sensor_index}
      ↓ Django RedisReader（网络模拟档）
  前端

本地模拟（无任何依赖）：
  Django LocalMockProvider（进程内生成）
      ↓ 本地模拟档
  前端
```

三个命名空间完全隔离，切换档位不影响彼此数据。

---

## 3. 项目目录

```text
RS485-Modbus-Concrete-Sensor-Monitor/
├── manage.py
├── requirements.txt
├── config/              Django 配置
├── app/
│   ├── templates/       前端页面
│   ├── static/          CSS / JS
│   ├── services/
│   │   ├── redis_reader.py      主数据源（读 Redis，支持双命名空间）
│   │   ├── local_mock.py        降级数据源
│   │   └── dashboard_service.py 三源路由
│   ├── api.py           Django Ninja 接口（支持 ?source= 参数）
│   └── views.py
├── collector/           Modbus TCP 采集器
│   ├── main.py          入口（读 MONITOR_REDIS_URL 环境变量）
│   ├── modbus_client.py FC03 TCP 客户端
│   ├── redis_writer.py  写 monitor:sensor:* 命名空间
│   ├── scheduler.py     多网关并发轮询
│   ├── parser.py        14 字节传感器块解析
│   ├── models.py        GatewayConfig / SensorSnapshot
│   └── config_loader.py 从 configs/gateways.json 加载配置
├── configs/
│   └── gateways.json    网关静态配置（ip / port / slave_id / sensor_count）
└── test/
    ├── README.md
    ├── mock_server.py   FastAPI 模拟器（--feed 写 monitor:test:* 命名空间）
    ├── load_test.py     压测脚本
    └── requirements.txt
```

---

## 4. 环境要求

- Python `3.11+`（验证环境：Python `3.13.5`，Django `6.0.5`）
- Redis（本地运行）

---

## 5. 安装

```bash
pip install -r requirements.txt
python3 manage.py migrate
```

---

## 6. 启动方式

### 方式一：本地模拟（无需 Redis，零依赖）

```bash
python3 manage.py runserver
```

打开 `http://127.0.0.1:8000/`，页面右上角选择 **本地模拟** 档即可看到数据。适合快速查看页面结构。

---

### 方式二：网络模拟（Redis + mock_server）

**前置：启动 Redis**

```bash
brew services start redis   # macOS
redis-cli ping              # 返回 PONG 即可
```

**启动 mock_server（写 monitor:test:* 命名空间）**

```bash
cd test
pip install -r requirements.txt
python mock_server.py --feed
```

**启动 Django**

```bash
python3 manage.py runserver
```

打开页面，选择 **网络模拟** 档查看实时数据。停止 mock_server 后，Redis key 在 10 秒内自动过期。

---

### 方式三：真实数据（接真实 RS485 网关）

配置 `configs/gateways.json`，然后启动采集器：

```bash
python3 collector/main.py
```

采集器连接各网关 Modbus TCP（默认端口 502），解包后写入 `monitor:sensor:*`。打开页面选择 **真实数据** 档即可。

---

## 7. Modbus 帧格式

每个传感器块固定 **14 字节**：

| 字段 | 字节数 | 类型 | 换算 |
|------|--------|------|------|
| 频率 | 2 | uint16 | 原始值 |
| 应变 | 4 | int32 | ÷ 1000 |
| 温度 | 2 | int16 | ÷ 100 |
| 最大应变 | 4 | int32 | ÷ 1000 |
| 状态码 | 2 | uint16 | 0=正常 |

响应帧总长度：`9 + N × 14` 字节（N 为传感器数，默认 16 → 233 字节）。

---

## 8. 压力测试

```bash
cd test

# 固定时长（默认 10 秒）
python load_test.py --base-url http://127.0.0.1:18000

# 无限循环，每 10 秒打印阶段统计，Ctrl+C 退出
python load_test.py --base-url http://127.0.0.1:18000 --duration 0

# 自定义并发和间隔
python load_test.py --base-url http://127.0.0.1:18000 --duration 0 --concurrency 50 --interval 30
```

---

## 9. API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 |
| `GET /api/summary?source=real` | 总览区数据（source: real \| fastapi \| mock） |
| `GET /api/matrix/{metric}?source=real` | 指标矩阵（metric: strain / temp / freq / max_strain） |
| `GET /api/history/{gateway_ip}/{sensor_index}?metric=strain` | 单测点历史（前端客户端侧积累） |

---

## 10. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MONITOR_REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接地址（Django + collector 共用） |
| `MONITOR_GATEWAY_COUNT` | `20` | 网关数量 |
| `MONITOR_SENSOR_COUNT` | `16` | 每网关测点数 |
| `MONITOR_REFRESH_MS` | `1000` | 前端刷新周期（毫秒） |

---

## 11. 指标量程

| 指标 | 量程 |
|------|------|
| 应变 | `-5000 ~ 5000` |
| 最大应变 | `-10000 ~ 10000` |
| 温度 | `-10 ~ 40` |
| 频率 | `1000 ~ 3000` |

---

## 12. 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 迁移
python3 manage.py migrate

# 启动 Django
python3 manage.py runserver

# 启动网络模拟（写 Redis monitor:test:*）
cd test && python mock_server.py --feed

# 启动真实采集器（写 Redis monitor:sensor:*）
python3 collector/main.py

# 压测
cd test && python load_test.py --base-url http://127.0.0.1:18000 --duration 0
```
