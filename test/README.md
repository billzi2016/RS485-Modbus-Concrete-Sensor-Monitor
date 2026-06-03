# test 目录说明

该目录用于放置独立测试原型，不属于主程序实现。

## 架构说明

`mock_server.py` 扮演 RS485 collector 的角色，负责向 Redis 写入模拟传感器数据。Django 始终从 Redis 读取数据，无论数据来源是真实 collector 还是 mock_server。

```
测试数据流：
  python mock_server.py --feed
      ↓ 每秒写 320 个 key（20 网关 × 16 传感器）TTL=10s
  Redis:6379  monitor:sensor:{ip}:{index}
      ↓ Django RedisReader 读取
  前端显示

真实数据流（生产）：
  RS485 传感器 → collector/modbus_client.py
      ↓ 写相同 key 格式
  Redis:6379
      ↓ Django RedisReader（代码不变）
  前端显示
```

## 文件说明

- `mock_server.py`
  - FastAPI 模拟服务，同时支持 Redis 数据写入模式（`--feed`）
  - 提供总览、矩阵、历史数据 HTTP 接口（供压测）
  - `--feed` 模式下持续向 Redis 写入传感器快照，模拟真实 collector
- `load_test.py`
  - 基于 `httpx` 的异步压力测试脚本，支持固定时长和无限循环两种模式
- `requirements.txt`
  - 测试原型依赖（包含 `redis[asyncio]`）

## 模拟规则

- 网关数量：`20`
- 每个网关设备数：`16`
- 模拟网段：`10.54.79.201 ~ 10.54.79.220`
- Redis key 格式：`monitor:sensor:{gateway_ip}:{sensor_index}`（sensor_index 从 1 开始）
- 默认指标范围：
  - 应变：`-5000 ~ 5000`
  - 温度：`-10 ~ 40`
  - 频率：`1000 ~ 3000`
  - 最大应变：`-10000 ~ 10000`

## 前置依赖

需要本地运行 Redis（默认 `localhost:6379`）：

```bash
# macOS
brew services start redis

# 验证
redis-cli ping  # 返回 PONG 即可
```

## 运行方式

**需要先进入 `test/` 目录**，因为 `test` 是 Python 标准库保留名：

```bash
cd test
pip install -r requirements.txt
```

### 模式一：向 Redis 写数据 + 启动 HTTP 接口（推荐）

```bash
python mock_server.py --feed
```

启动后 mock_server 会同时：
1. 每秒向 Redis 写入所有传感器快照（Django 打开"测试数据"开关即可看到数据）
2. 在 `http://127.0.0.1:18000` 提供 HTTP 接口供压测使用

停止 mock_server 后，Redis key 在 10 秒内自动过期，Django 降级到本地 mock。

### 模式二：仅启动 HTTP 接口（不写 Redis）

```bash
# 直接用 uvicorn（只跑 HTTP，不写 Redis）
uvicorn mock_server:app --reload --port 18000

# 或
python mock_server.py
```

### 模式三：自定义参数

```bash
python mock_server.py --feed \
  --redis-url redis://localhost:6379 \
  --feed-interval 0.5 \
  --port 18000
```

## 压力测试

```bash
cd test

# 固定时长（默认 10 秒）
python load_test.py --base-url http://127.0.0.1:18000

# 无限循环，每 10 秒打印一次阶段统计，Ctrl+C 退出并打印汇总
python load_test.py --base-url http://127.0.0.1:18000 --duration 0

# 自定义：并发 50，每轮 30 秒统计
python load_test.py --base-url http://127.0.0.1:18000 --duration 0 --concurrency 50 --interval 30
```

## 网络假设

当前测试按本机局域网环境编写，模拟网关地址使用 `10.54.79.201 ~ 10.54.79.220`（`/24` 网段）。

如需模拟更大的 `/16` 工业网段，可通过 Docker 桥接网络、ZeroTier、WireGuard 等方式构造虚拟网络。当前 `test/` 目录不引入这些方案。
