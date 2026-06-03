# 项目目录说明

本文档分为两部分：

- 当前实际目录树
- 后续建议目录树

其中“当前实际目录树”描述仓库里已经存在的文件；  
“后续建议目录树”用于约束后面正式进入主程序开发时的标准结构。

---

## 1. 当前实际目录树

```text
RS485-Modbus-Concrete-Sensor-Monitor/
├── DOC_TREE.md
├── PRD.md
├── TASK.md
├── app/
│   ├── __init__.py
│   ├── admin.py
│   ├── api.py
│   ├── apps.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── dashboard_service.py
│   │   ├── local_mock.py
│   │   ├── mock_api_client.py
│   │   └── redis_reader.py
│   ├── migrations/
│   │   └── __init__.py
│   ├── models.py
│   ├── static/
│   │   └── app/
│   │       ├── css/
│   │       │   └── dashboard.css
│   │       └── js/
│   │           └── dashboard.js
│   ├── templates/
│   │   └── app/
│   │       └── dashboard.html
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── collector/
│   ├── __init__.py
│   ├── config_loader.py
│   ├── main.py
│   ├── modbus_client.py
│   ├── models.py
│   ├── parser.py
│   ├── redis_writer.py
│   └── scheduler.py
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── configs/
│   └── gateways.json
├── db.sqlite3
├── manage.py
└── test/
    ├── README.md
    ├── load_test.py
    ├── mock_server.py
    └── requirements.txt
```

### 1.1 当前文件说明

- `PRD.md`
  - 项目的产品需求文档
  - 当前已经明确了跨平台重构方向、采集架构、Redis 缓存、Django + Ninja + Template 的展示层方案

- `DOC_TREE.md`
  - 当前文档本身
  - 用来说明项目目录结构和后续建议结构

- `TASK.md`
  - 项目任务清单
  - 用于后续分阶段推进开发

- `manage.py`
  - Django 标准管理入口
  - 后续所有 Django 管理命令都从这里执行

- `config/`
  - Django 项目级配置目录
  - 当前已经完成最传统骨架初始化

- `app/`
  - Django 标准业务应用目录
  - 当前已接入工控首页、`Django Ninja` API、页面静态资源和本地 mock 数据服务

- `collector/`
  - 独立采集器模块
  - 当前已完成骨架和固定报文解析入口

- `configs/`
  - 静态配置目录
  - 当前包含 `20` 个测试网关的 `gateways.json`

- `db.sqlite3`
  - Django 本地开发数据库
  - 由标准迁移命令生成

- `test/`
  - 独立测试原型目录
  - 不属于正式主程序
  - 当前用于模拟 20 个网关、每个网关 16 个设备的数据接口和压力测试

### 1.2 Django 骨架目录说明

```text
manage.py
config/
├── __init__.py
├── asgi.py
├── settings.py
├── urls.py
└── wsgi.py
app/
├── __init__.py
├── admin.py
├── api.py
├── apps.py
├── services/
│   ├── __init__.py
│   ├── dashboard_service.py
│   ├── local_mock.py
│   ├── mock_api_client.py
│   └── redis_reader.py
├── migrations/
│   └── __init__.py
├── models.py
├── static/
│   └── app/
│       ├── css/
│       │   └── dashboard.css
│       └── js/
│           └── dashboard.js
├── templates/
│   └── app/
│       └── dashboard.html
├── tests.py
├── urls.py
└── views.py
```

- `manage.py`
  - Django 标准命令入口

- `config/settings.py`
  - 项目级基础配置
  - 当前已注册 `app`

- `config/urls.py`
  - 项目级总路由
  - 当前已接入：
    - `admin/`
    - `api/`
    - `app.urls`

- `app/views.py`
  - 当前提供最小首页占位

- `app/urls.py`
  - 当前提供 app 级基础路由

- `app/api.py`
  - 当前提供健康检查、总览、矩阵、历史接口

- `app/services/`
  - 页面层数据服务
  - 当前支持：
    - 外部 mock 服务代理
    - 本地 mock 数据回退
    - Redis 读取器占位

- `app/templates/app/dashboard.html`
  - 当前工控风格首页模板

- `app/static/app/css/dashboard.css`
  - 当前工控风格样式

- `app/static/app/js/dashboard.js`
  - 当前前端轮询、Tab 切换、矩阵渲染、历史曲线逻辑

### 1.3 collector 目录说明

```text
collector/
├── __init__.py
├── config_loader.py
├── main.py
├── modbus_client.py
├── models.py
├── parser.py
├── redis_writer.py
└── scheduler.py
```

- `collector/config_loader.py`
  - 静态网关配置加载器

- `collector/parser.py`
  - 按 14 字节布局进行整型位移解算

- `collector/scheduler.py`
  - asyncio 调度器骨架

- `collector/modbus_client.py`
  - Modbus TCP 客户端占位

- `collector/redis_writer.py`
  - Redis 写入器占位

### 1.4 test 目录说明

```text
test/
├── README.md
├── load_test.py
├── mock_server.py
└── requirements.txt
```

- `test/README.md`
  - 说明测试目录用途
  - 说明为什么当前按 `/24` 网段模拟，而不是强行按 `/16`
  - 说明后续如果需要 `/16`，可通过虚拟化、容器或覆盖网络模拟

- `test/mock_server.py`
  - 基于 FastAPI 的模拟服务
  - 提供总览、矩阵数据、历史曲线接口
  - 使用 `10.54.79.201 ~ 10.54.79.220` 作为模拟网关地址

- `test/load_test.py`
  - 异步压力测试脚本
  - 对模拟接口进行轮询压测

- `test/requirements.txt`
  - 测试原型依赖

---

## 2. 后续建议目录树

后续正式进入主程序开发时，Django 必须采用最传统、最标准的项目结构。

要求如下：

- 必须使用 `manage.py`
- 必须保留项目级 `config/`
- 必须使用 Django 原始标准目录布局
- 业务逻辑放在独立 `app/` 中
- 不使用非常规目录魔改结构

建议目录树如下：

```text
RS485-Modbus-Concrete-Sensor-Monitor/
├── PRD.md
├── DOC_TREE.md
├── TASK.md
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── app/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── managers.py
│   ├── models.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── redis_reader.py
│   │   └── snapshot_service.py
│   ├── templates/
│   │   └── app/
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       └── partials/
│   ├── static/
│   │   └── app/
│   │       ├── css/
│   │       └── js/
│   ├── urls.py
│   ├── api.py
│   ├── views.py
│   └── tests/
│       ├── __init__.py
│       ├── test_api.py
│       └── test_views.py
├── collector/
│   ├── __init__.py
│   ├── main.py
│   ├── config_loader.py
│   ├── scheduler.py
│   ├── modbus_client.py
│   ├── parser.py
│   ├── redis_writer.py
│   └── models.py
├── configs/
│   └── gateways.json
└── test/
    ├── README.md
    ├── load_test.py
    ├── mock_server.py
    └── requirements.txt
```

---

## 3. Django 结构约束

### 3.1 项目初始化方式

后续创建 Django 主程序时，必须采用标准命令流：

```bash
django-admin startproject config .
python manage.py startapp app
```

说明：

- `config` 是项目级配置目录
- `app` 是主业务应用目录
- 所有管理命令都通过 `manage.py` 执行

### 3.2 为什么必须保持传统结构

原因如下：

- 便于维护
- 便于后续查资料和排错
- 便于按 Django 常规方式组织模板、静态文件、路由和配置
- 便于多人协作时快速理解项目
- 避免为了“看起来高级”而引入不必要的结构复杂度

### 3.3 config 目录职责

`config/` 只负责项目级内容：

- `settings.py`
- `urls.py`
- `asgi.py`
- `wsgi.py`

不在 `config/` 中塞业务逻辑。

### 3.4 app 目录职责

`app/` 负责核心 Web 展示逻辑：

- Django Template 页面
- Django Ninja API
- 视图函数
- Redis 读取服务
- 页面静态资源

### 3.5 collector 目录职责

`collector/` 与 Django 主应用解耦，作为独立采集模块存在：

- 网关调度
- Modbus TCP 读写
- 固定报文解析
- Redis 写入

它不放入 Django 的 `app/` 中，避免将采集器和 Web 请求生命周期绑死。

---

## 4. 当前状态与后续关系

当前仓库仍处于：

- 需求整理阶段
- 结构设计阶段
- 测试原型阶段
- Django 骨架初始化阶段
- Django 页面原型阶段
- collector 骨架阶段

尚未进入：

- 真实网关采集联调
- Redis 正式集成
- 长期历史持久化

因此，当前目录树已经进入“文档 + test 原型 + Django 标准骨架”状态；  
后续建议目录树仍然用于约束正式业务开发阶段的继续扩展。
