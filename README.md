# RS485 Modbus Concrete Sensor Monitor

基于 `Python + Django + Django Ninja` 的混凝土传感器实时监测系统。

---

## 1. 当前状态

### 已完成

- Django 项目结构 + Django Ninja API
- 工控风格监控首页（高密度矩阵、多 Tab 指标、10 分钟历史趋势）
- **Redis 数据链路**：Django 直接从 Redis 读取传感器数据
- **mock_server Redis 写入模式**：`python mock_server.py --feed` 模拟真实 collector 向 Redis 写数据
- 本地 mock 降级（Redis 不可用时自动回退）
- `test/` 独立测试原型 + 压测脚本
- `collector/` 骨架（配置加载、调度器、报文解析器）

### 未完成

- 真实 Modbus TCP 采集联调
- 长期历史持久化
- 告警模块

---

## 2. 数据流架构

```
测试数据（开发 / 联调）：
  python test/mock_server.py --feed
      ↓ 每秒写 320 key（20 网关 × 16 传感器）TTL=10s
  Redis:6379  monitor:sensor:{ip}:{sensor_index}
      ↓ Django RedisReader
  前端

真实数据（生产）：
  RS485 传感器 → collector/modbus_client.py
      ↓ 写相同 key 格式
  Redis:6379
      ↓ Django RedisReader（代码不变）
  前端
```

切换数据来源只需要切换"谁在往 Redis 写"，Django 侧代码不变。

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
│   │   ├── redis_reader.py    主数据源（读 Redis）
│   │   ├── local_mock.py      降级数据源
│   │   └── dashboard_service.py
│   ├── api.py           Django Ninja 接口
│   └── views.py
├── collector/           RS485 采集骨架（待实现）
├── configs/
│   └── gateways.json    网关静态配置
└── test/
    ├── README.md
    ├── mock_server.py   FastAPI 模拟 collector（支持 --feed 写 Redis）
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

### 方式一：最快启动（无 Redis，使用本地 mock 降级）

```bash
python3 manage.py runserver
```

Django 连不上 Redis 时自动降级到进程内 mock 数据，适合快速查看页面结构。

### 方式二：完整联调（Redis + mock_server 写入）

**前置：启动 Redis**

```bash
brew services start redis   # macOS
# 验证：redis-cli ping  → 返回 PONG
```

**启动 mock_server（往 Redis 写数据）**

```bash
cd test
pip install -r requirements.txt
python mock_server.py --feed
```

**启动 Django**

```bash
python3 manage.py runserver
```

打开 `http://127.0.0.1:8000/`，点击页面上的"测试数据"开关即可看到实时数据。

停止 mock_server 后，Redis key 在 10 秒内自动过期，Django 自动降级到本地 mock。

---

## 7. 压力测试

```bash
cd test

# 固定时长（默认 10 秒）
python load_test.py --base-url http://127.0.0.1:18000

# 无限循环，每 10 秒打印阶段统计，Ctrl+C 退出
python load_test.py --base-url http://127.0.0.1:18000 --duration 0

# 自定义并发和间隔
python load_test.py --base-url http://127.0.0.1:18000 --duration 0 --concurrency 50 --interval 30
```

注意：压测需要 mock_server 的 HTTP 接口在线，与 `--feed` 模式互不影响（可以同时跑）。

---

## 8. API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 |
| `GET /api/summary` | 总览区数据（在线网关数、异常测点数等） |
| `GET /api/matrix/{metric}` | 指标矩阵（metric: strain / temp / freq / max_strain） |
| `GET /api/history/{gateway_ip}/{sensor_index}?metric=strain` | 单测点历史（前端现由客户端自行积累，此接口保留兼容） |

---

## 9. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MONITOR_REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接地址 |
| `MONITOR_GATEWAY_COUNT` | `20` | 网关数量 |
| `MONITOR_SENSOR_COUNT` | `16` | 每网关测点数 |
| `MONITOR_REFRESH_MS` | `1000` | 前端刷新周期（毫秒） |

---

## 10. 指标量程

| 指标 | 量程 |
|------|------|
| 应变 | `-5000 ~ 5000` |
| 最大应变 | `-10000 ~ 10000` |
| 温度 | `-10 ~ 40` |
| 频率 | `1000 ~ 3000` |

---

## 11. 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 迁移
python3 manage.py migrate

# 启动 Django
python3 manage.py runserver

# 启动 mock_server（写 Redis + HTTP 接口）
cd test && python mock_server.py --feed

# 压测
cd test && python load_test.py --base-url http://127.0.0.1:18000 --duration 0
```

---

## 12. 相关文档

- [PRD.md](PRD.md) — 需求文档
- [DOC_TREE.md](DOC_TREE.md) — 目录结构说明
- [TASK.md](TASK.md) — 任务清单
- [test/README.md](test/README.md) — 测试目录详细说明
