# TripManner 后端 + 数据库实施计划

> 版本：v2.0
> 更新日期：2026-05-17
> 基于论文第5章系统实现要求，以 Supabase (PostgreSQL) 为数据库

---

## 1. 技术栈确认

| 层级 | 选型 | 说明 |
|------|------|------|
| 后端框架 | Python FastAPI | 异步高性能，原生支持SSE |
| 数据库 | **Supabase (PostgreSQL)** | 云端托管，免运维 |
| ORM | SQLAlchemy 2.0 | 已有模型定义，改连接串即可 |
| DB驱动 | psycopg2-binary | PostgreSQL Python驱动 |
| 认证方案 | **BCrypt + Session/数据库直接校验** | 论文要求，非JWT |
| LLM | DeepSeek API (httpx async) | 通用城市Agent |
| SSE | sse-starlette | 流式输出 |
| 算法推理 | PyTorch (EKD-Trip, CrossTrip) | 加载训练好的模型 |

---

## 2. Supabase 连接信息

```
Host: db.mclyasgucknjdykizmtc.supabase.co
Port: 5432
Database: postgres
User: postgres
Password: [YOUR-PASSWORD]  ← 需要你填入真实密码
Connection String: postgresql://postgres:[PASSWORD]@db.mclyasgucknjdykizmtc.supabase.co:5432/postgres
```

---

## 3. 数据库表设计（与论文表5.2一致）

### 3.1 users 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 自增主键 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| password_hash | VARCHAR(200) | NOT NULL | BCrypt加密密码 |
| nickname | VARCHAR(50) | NULL | 昵称 |
| avatar | VARCHAR(500) | NULL | 头像URL |
| preferences | JSONB | NULL | 旅行偏好(兴趣类别/出行风格/同行人/预算) |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

### 3.2 pois 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 自增主键 |
| name | VARCHAR(200) | NOT NULL | POI名称 |
| city | VARCHAR(100) | NOT NULL, INDEX | 所属城市 |
| latitude | FLOAT | NOT NULL | 纬度 |
| longitude | FLOAT | NOT NULL | 经度 |
| category | VARCHAR(100) | NULL | 类别 |
| description | TEXT | NULL | 描述 |
| visit_duration_min | INTEGER | NULL | 建议停留时长(分钟) |
| rating | FLOAT | NULL | 评分 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

### 3.3 routes 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 自增主键 |
| user_id | INTEGER | FK(users.id), INDEX | 用户外键 |
| city | VARCHAR(100) | NOT NULL | 目的城市 |
| algorithm_used | VARCHAR(50) | NOT NULL | 'EKD-Trip' / 'CrossTrip' / 'DeepSeek-Agent' |
| query_input | JSONB | NULL | 原始查询五元组 |
| route_result | JSONB | NULL | 路线结果(POI序列) |
| intent_data | JSONB | NULL | 意图可视化数据 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

### 3.4 dialogs 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 自增主键 |
| dialog_id | VARCHAR(36) | UNIQUE, INDEX | UUID对话标识 |
| user_id | INTEGER | FK(users.id), INDEX | 用户外键 |
| title | VARCHAR(200) | NULL | 对话标题 |
| messages | JSONB | NULL | 消息列表JSON |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

### 3.5 user_checkins 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 自增主键 |
| user_id | INTEGER | FK(users.id), INDEX | 用户外键 |
| poi_id | INTEGER | FK(pois.id), NULL | POI外键 |
| city | VARCHAR(100) | INDEX | 签到城市 |
| checkin_time | TIMESTAMP | NOT NULL | 签到时间 |

---

## 4. 实施阶段划分

### Phase 1：数据库连接 & 认证模块（基础设施）

**目标**：将后端从内存存储迁移到 Supabase PostgreSQL，实现真实的用户注册/登录。

**修改文件：**
- `backend/config.py` — DATABASE_URL 改为 PostgreSQL 连接串
- `backend/database.py` — 确认 SQLAlchemy engine 配置兼容 PostgreSQL
- `backend/requirements.txt` — 添加 `psycopg2-binary`
- `backend/models/user.py` — 调整字段类型(TEXT→JSONB)
- `backend/routers/auth.py` — 从 fake_users_db 改为数据库查询，认证改为 Session/数据库直接校验
- `backend/.env` — 存放真实连接串和密钥（不提交git）

**认证流程改动（论文要求：BCrypt + 数据库直接校验）：**
```
登录请求 → 查数据库用户名 → BCrypt验证密码 → 返回session token
后续请求 → 携带token → 查数据库验证token有效性
```

注：为简化实现，可以保留JWT作为token格式（前端已适配），但验证时直接查数据库确认用户存在性，符合论文中"直接查询数据库比对账号凭证"的描述。

### Phase 2：数据持久化（对话 & 路线记录）

**目标**：对话历史和路线规划记录持久化到数据库。

**修改文件：**
- `backend/routers/chat.py` — 对话保存/读取改为数据库操作
- `backend/routers/plan.py` — 路线记录存入routes表
- `backend/services/dialog_manager.py` — 从内存sessions改为DB读写
- `backend/models/` — 添加 SQLAlchemy relationship() 关联

### Phase 3：算法服务集成

**目标**：真正调用 EKD-Trip 和 CrossTrip 算法模型推理。

**修改文件：**
- `backend/services/ekd_trip.py` — 加载 PyTorch 模型，实现 predict()
- `backend/services/cross_city.py` — 加载 PyTorch 模型，实现 predict()
- `backend/services/route_decision.py` — Mock/Real 模式切换完善

**EKD-Trip 集成要点：**
- 加载训练好的模型权重 (从 `algorithm/EKDTrip/` 目录)
- 输入：start_poi_id, end_poi_id, start_time, end_time, num_pois
- 输出：POI序列 + travel_mode + confidence + distance_curve

**CrossTrip 集成要点：**
- 加载训练好的模型权重 (从 `algorithm/CrossTrip/` 目录)
- 输入：user_id, source_city, target_city, start_poi, end_poi, start_time, end_time, num_pois
- 输出：POI序列 + preference_factors + transfer_weights + blend_weight_eta

### Phase 4：DeepSeek LLM Agent 集成

**目标**：对不在数据集中的城市，通过 DeepSeek API 生成路线。

**修改文件：**
- `backend/services/llm_agent.py` — 实现真实API调用 + ReAct推理
- `backend/routers/chat.py` — 流式SSE推送LLM输出

**Agent设计（ReAct模式）：**
```
Prompt模板:
  你是TripManner旅行规划助手。根据用户需求规划路线。
  用户需求: {destination_city}, 从{start_poi}到{end_poi}, {start_time}-{end_time}, {num_pois}个景点

  输出格式要求:
  - 每个POI: 名称、类别、经纬度、建议停留时长、行程亮点描述
  - 按地理位置优化顺序
  - 确保总时间在用户指定范围内
```

**流式输出：**
- 使用 httpx AsyncClient 流式接收 DeepSeek 响应
- 解析每个 token，识别出完整POI后立即发送 `poi_added` SSE事件
- 文本逐token通过 `route_text` 事件推送

### Phase 5：SSE 流式输出完整实现

**目标**：真实算法结果通过SSE流式推送给前端（与前端mock的SSE事件格式完全一致）。

**SSE事件协议（保持与前端一致）：**
```
event: thinking
data: {"status": "planning", "text": "正在为您规划路线...", "algorithm": "EKD-Trip"}

event: route_text
data: {"delta": "第1站：皇居..."}

event: poi_added
data: {"poi": {"poi_id": 1001, "name": "...", "category": "...", ...}}

event: intent_data
data: {"travel_mode": "approaching", "travel_mode_confidence": 0.87, ...}

event: done
data: {"plan_id": "xxx", "algorithm": "EKD-Trip", "is_mock": false}
```

---

## 5. 文件变更清单

| 文件 | 操作 | Phase |
|------|------|-------|
| `backend/.env` | 新建 | P1 |
| `backend/config.py` | 修改(DATABASE_URL, SECRET_KEY从env读取) | P1 |
| `backend/database.py` | 修改(PostgreSQL兼容) | P1 |
| `backend/requirements.txt` | 添加psycopg2-binary, httpx | P1 |
| `backend/models/user.py` | 修改(JSONB类型) | P1 |
| `backend/models/route.py` | 修改(添加query_input, intent_data字段) | P1 |
| `backend/models/dialog.py` | 修改(messages字段改JSONB) | P1 |
| `backend/routers/auth.py` | 重写(数据库认证) | P1 |
| `backend/routers/user.py` | 修改(数据库读写) | P1 |
| `backend/routers/chat.py` | 修改(数据库持久化) | P2 |
| `backend/routers/plan.py` | 修改(数据库存储) | P2 |
| `backend/services/dialog_manager.py` | 修改(DB替代内存) | P2 |
| `backend/services/ekd_trip.py` | 重写(算法集成) | P3 |
| `backend/services/cross_city.py` | 重写(算法集成) | P3 |
| `backend/services/llm_agent.py` | 重写(DeepSeek API) | P4 |
| `backend/routers/chat.py` | 完善(SSE流式) | P5 |

---

## 6. 环境变量配置 (.env)

```env
# Supabase PostgreSQL
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.mclyasgucknjdykizmtc.supabase.co:5432/postgres

# Security
SECRET_KEY=your-random-secret-key-at-least-32-chars

# DeepSeek API
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# App Config
USE_MOCK_DATA=true
SESSION_EXPIRE_HOURS=24
```

---

## 7. 建表SQL（Phase 1 在 Supabase SQL Editor 执行）

```sql
-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    nickname VARCHAR(50),
    avatar VARCHAR(500),
    preferences JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- POIs
CREATE TABLE IF NOT EXISTS pois (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    category VARCHAR(100),
    description TEXT,
    visit_duration_min INTEGER,
    rating DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pois_city ON pois(city);

-- Routes
CREATE TABLE IF NOT EXISTS routes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    city VARCHAR(100) NOT NULL,
    algorithm_used VARCHAR(50) NOT NULL,
    query_input JSONB,
    route_result JSONB,
    intent_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_routes_user_id ON routes(user_id);

-- Dialogs
CREATE TABLE IF NOT EXISTS dialogs (
    id SERIAL PRIMARY KEY,
    dialog_id VARCHAR(36) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(200),
    messages JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dialogs_user_id ON dialogs(user_id);
CREATE INDEX IF NOT EXISTS idx_dialogs_dialog_id ON dialogs(dialog_id);

-- User Checkins
CREATE TABLE IF NOT EXISTS user_checkins (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    poi_id INTEGER REFERENCES pois(id),
    city VARCHAR(100),
    checkin_time TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checkins_user_id ON user_checkins(user_id);
CREATE INDEX IF NOT EXISTS idx_checkins_city ON user_checkins(city);
```

---

## 8. 前端适配要点

前端目前已有 mock fallback 机制，后端上线后只需：
1. 在 Settings 页面切换为 "Real" 模式
2. 前端 `api/auth.js` 已有 try/catch fallback，无需修改
3. SSE 事件格式后端与前端 mock 完全一致，无需改前端逻辑
4. 算法标签显示已改为 "EKD-Trip" / "CrossTrip" / "DeepSeek-Agent"

---

## 9. 实施优先级建议

```
Phase 1 (数据库+认证) ──→ Phase 2 (持久化) ──→ Phase 4 (DeepSeek) ──→ Phase 3 (算法) ──→ Phase 5 (SSE)
     ↑ 建议先做                                      ↑ 可独立于P3        ↑ 需要模型文件      ↑ 整合收尾
```

建议先做 P1+P2+P4，因为：
- P1+P2 让系统有真实数据持久化，告别内存存储
- P4 (DeepSeek) 不依赖本地模型文件，只需API key即可实现
- P3 (算法集成) 需要确认模型训练完成并有可用权重文件
- P5 是最后的整合工作

---

## 10. 验证标准

| Phase | 验证方式 | 通过标准 |
|-------|---------|---------|
| P1 | Postman测试注册/登录 | 用户数据持久化到Supabase，重启后仍可登录 |
| P2 | 前端创建对话→关闭浏览器→重新打开 | 对话记录从数据库恢复 |
| P3 | 输入东京查询 | 返回真实算法推理的POI序列和intent_data |
| P4 | 输入"曼谷"查询 | DeepSeek实时生成路线，SSE流式输出 |
| P5 | 全流程端到端 | 前端流式渲染+地图动态绘制+意图面板正常显示 |
