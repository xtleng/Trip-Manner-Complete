# TripManner — 智能旅行规划系统 产品需求文档（PRD）

> **系统全称**：TripManner: Intelligent Travel Planning System Based on Complex User Intent Inference
> **中文名称**：TripManner — 基于复杂用户意图推断的智能旅行规划系统
> **文档版本**：v1.2
> **最后更新**：2026-04-27

---

## 1 系统概述

### 1.1 项目背景

本系统是毕业论文《基于复杂用户意图推断的旅行路线推荐》的配套实现系统。论文前四章分别提出了：

- **第三章 EKD-Trip**：基于知识蒸馏与显式意图增强的单城市旅行路线推荐算法。通过Privileged Knowledge Distillation将用户历史轨迹信息蒸馏到查询编码器中，并引入Travel Mode（接近/远离/U型/不规则）分类任务显式建模用户空间移动意图。
- **第四章 CrossCityLLMCPR**：融合多维用户偏好意图的跨城市旅行路线推荐算法。通过LLM语义偏好提取、K=4维正交偏好解耦、自适应偏好迁移与城市群体记忆融合，实现跨城市冷启动场景下的路线推荐。

TripManner系统将上述两个算法集成到一个完整的Web应用中，使其能够在实际旅行规划场景中落地运行，同时通过可视化用户偏好意图来增强系统的可解释性。

### 1.2 系统定位

TripManner是一个**面向终端用户的智能旅行规划Web系统**，核心特色为：

1. **算法驱动的路线推荐**：对数据集覆盖城市调用论文算法，对其他城市通过LLM Agent实现通用规划
2. **用户意图可视化**：将算法推理过程中的用户偏好意图（travel mode、偏好因子、迁移权重等）以可视化方式呈现，增强系统可解释性和可信度
3. **引导式对话与流式输出**：当用户输入信息不完整时，系统通过多轮引导对话补全查询五元组；路线结果以流式（Streaming）方式逐步输出自然语言描述，同时地图上动态逐步绘制路线
4. **Mock/Real双模式**：支持mock数据演示和真实算法调用之间的无缝切换

### 1.3 目标用户

- 有出行规划需求的普通旅行者
- 论文评审专家 / 答辩评委（演示场景）

---

## 2 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| **前端框架** | Vue 3 + Vite | 现代化前端构建方案 |
| **UI组件库** | Element Plus | 企业级Vue 3组件库 |
| **地图引擎** | Leaflet + OpenStreetMap | 开源方案，无需授权Key |
| **数据可视化** | ECharts | 用于意图可视化图表（雷达图、曲线图、热力图等） |
| **HTTP客户端** | Axios | 前后端数据通信 |
| **后端框架** | Python FastAPI | 统一后端服务，异步高性能 |
| **大语言模型** | DeepSeek API | 通用城市路线规划的LLM Agent |
| **数据库** | MySQL 8.0 | 结构化数据存储 |
| **认证方案** | BCrypt + Session | 基于密码加密的直接校验认证 |

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户层 (User Layer)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ 对话交互  │  │ 地图可视化│  │ 意图可视化│  │ 用户管理/偏好设置│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬──────────┘ │
│       │             │             │                 │            │
├───────┼─────────────┼─────────────┼─────────────────┼────────────┤
│       ▼             ▼             ▼                 ▼            │
│                     平台层 (Platform Layer)                       │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                  路由决策引擎 (Route Decision Engine)          ││
│  │  ┌────────────┬────────────────────┬───────────────────────┐ ││
│  │  │ EKD-Trip   │ CrossCityLLMCPR    │ DeepSeek LLM Agent    │ ││
│  │  │ (单城市)   │ (跨城市)           │ (通用城市)            │ ││
│  │  └─────┬──────┴──────────┬─────────┴──────────┬────────────┘ ││
│  │        │     Mock/Real 开关                    │             ││
│  │        ▼                 ▼                     ▼             ││
│  │  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐   ││
│  │  │Mock数据  │    │ 算法推理服务  │    │ DeepSeek API     │   ││
│  │  └──────────┘    └──────────────┘    └──────────────────┘   ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                     数据层 (Data Layer)                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐│
│  │ 用户数据    │  │ POI数据    │  │ 路线记录    │  │ Mock数据   ││
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘│
│                       MySQL 8.0                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 前后端分离架构

```
┌───────────────────┐          ┌───────────────────────────────────┐
│    Frontend        │          │           Backend (FastAPI)       │
│    (Vue 3 + Vite)  │  HTTP    │                                   │
│                    │◄────────►│  ┌─────────────────────────────┐  │
│  • Element Plus    │  REST    │  │     API Router               │  │
│  • Leaflet/OSM     │  API     │  │  /api/auth  /api/plan       │  │
│  • ECharts         │          │  │  /api/chat  /api/config     │  │
│  • Axios           │          │  └──────────┬──────────────────┘  │
│                    │          │             │                     │
│  Port: 5173        │          │  ┌──────────▼──────────────────┐  │
└───────────────────┘          │  │   Service Layer              │  │
                                │  │  • RouteDecisionService     │  │
                                │  │  • EKDTripService           │  │
                                │  │  • CrossCityService         │  │
                                │  │  • LLMAgentService          │  │
                                │  │  • MockDataService          │  │
                                │  └──────────┬──────────────────┘  │
                                │             │                     │
                                │  ┌──────────▼──────────────────┐  │
                                │  │   Data Access Layer          │  │
                                │  │  • MySQL (SQLAlchemy ORM)    │  │
                                │  │  • DeepSeek API Client       │  │
                                │  └─────────────────────────────┘  │
                                │                                   │
                                │  Port: 8000                       │
                                └───────────────────────────────────┘
```

---

## 3 功能性需求分析

TripManner系统的功能性需求划分为六个模块：用户管理模块、智能路线规划模块、意图可视化模块、地图可视化模块、对话交互模块和数据管理模块。

### 3.1 用户管理模块

用户管理模块负责系统的用户认证、个人信息管理和偏好设置。

**功能清单**：
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 用户注册 | 用户名 + 密码注册，密码加密存储 | P0 |
| 用户登录 | 密码加密校验认证（BCrypt + 数据库直接比对） | P0 |
| 用户偏好设置 | 设置旅行兴趣标签、偏好出行方式、同行人类型 | P0 |
| 个人信息管理 | 修改头像、昵称、基本信息 | P1 |
| 历史规划查看 | 查看过往旅行规划记录 | P1 |

**偏好设置字段**：
- `interested_categories`: 兴趣POI类别（如：文化古迹、自然风光、美食、购物、娱乐）
- `travel_style`: 出行风格（如：深度游、打卡游、休闲游）
- `companion_type`: 同行人类型（如：独自、情侣、家庭、朋友）
- `budget_level`: 预算级别（经济、舒适、高端）

### 3.2 智能路线规划模块（核心模块）

本模块是系统的核心，负责接收用户的旅行查询请求，通过路由决策引擎选择合适的算法或LLM Agent进行路线规划。

#### 3.2.1 路由决策引擎

路由决策引擎根据用户查询的目的地城市自动判断应调用哪种算法：

```
用户查询输入
    │
    ▼
┌──────────────────────────────┐
│   提取目的城市 / 判断场景类型  │
└──────────────┬───────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
 单城市内    跨城市      其他城市
 旅行规划   旅行规划     旅行规划
    │          │          │
    ▼          ▼          ▼
 目的城市∈   涉及城市∈   不在数据集
 {Glasgow,   {New York,  覆盖范围内
  Osaka,      Los Angeles,
  Toronto,    San Francisco}
  Tokyo}      │          │
    │          │          │
    ▼          ▼          ▼
 EKD-Trip   CrossCity   DeepSeek
 算法        LLMCPR     LLM Agent
             算法
```

**单城市数据集城市**（第三章EKD-Trip）：Glasgow, Osaka, Toronto, Tokyo
**跨城市数据集城市**（第四章CrossCityLLMCPR）：New York, Los Angeles, San Francisco

#### 3.2.2 查询输入格式

用户可通过自然语言或结构化表单提交查询，系统解析为标准五元组：

```
<departure_city, start_time, destination_city, end_time, num_stops>
```

| 字段 | 类型 | 描述 | 示例 |
|------|------|------|------|
| `departure_city` | string | 出发城市 | "Tokyo" |
| `start_time` | datetime | 出发时间 | "2026-05-01 09:00" |
| `destination_city` | string | 目的城市 | "Tokyo"（同城）/ "Los Angeles"（跨城） |
| `end_time` | datetime | 结束时间 | "2026-05-01 18:00" |
| `num_stops` | int | 期望途经点数 | 5 |

#### 3.2.3 EKD-Trip 算法接口（单城市）

**调用条件**：`destination_city ∈ {Glasgow, Osaka, Toronto, Tokyo}`

**接口定义**：
```
POST /api/algorithm/ekd-trip
```

**请求参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `user_id` | int | 用户ID |
| `start_poi_id` | int | 起点POI ID |
| `end_poi_id` | int | 终点POI ID |
| `start_time` | int | 出发时间（24小时制时间槽，0-23） |
| `end_time` | int | 结束时间 |
| `num_pois` | int | 期望途经POI数量 |

**返回数据**：
```json
{
  "algorithm": "EKD-Trip",
  "city": "Tokyo",
  "route": [
    {
      "poi_id": 101,
      "name": "浅草寺 (Senso-ji)",
      "category": "Temple & Shrine",
      "latitude": 35.7148,
      "longitude": 139.7967,
      "recommended_duration_min": 60,
      "visit_order": 1
    }
  ],
  "intent_data": {
    "travel_mode": "approaching",
    "travel_mode_confidence": 0.87,
    "distance_to_destination_curve": [5.2, 4.1, 3.3, 2.0, 0.8],
    "query_representation_similarity": 0.82
  },
  "generation_confidence": 0.85
}
```

**Travel Mode 四种分类**（对应第三章3.3节）：

| Mode | 中文名 | 距离序列特征 | 说明 |
|------|--------|-------------|------|
| `approaching` | 接近模式 | 单调递减 | 持续向目的地靠近 |
| `moving_away` | 远离模式 | 单调递增 | 先远离目的地再折返 |
| `u_turn` | U型模式 | 高斯曲线 | 先远后近，呈U型 |
| `irregular` | 不规则模式 | 无规律 | 无明显空间趋势 |

#### 3.2.4 CrossCityLLMCPR 算法接口（跨城市）

**调用条件**：查询涉及跨城市，且目标城市 ∈ {New York, Los Angeles, San Francisco}

**接口定义**：
```
POST /api/algorithm/cross-city
```

**请求参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `user_id` | int | 用户ID |
| `source_city` | string | 源城市（用户有签到历史的城市） |
| `target_city` | string | 目标城市 |
| `user_profile` | object | 用户画像（偏好标签等） |
| `query_conditions` | object | 查询条件（时间、POI数等） |

**返回数据**：
```json
{
  "algorithm": "CrossCityLLMCPR",
  "source_city": "New York",
  "target_city": "Los Angeles",
  "route": [
    {
      "poi_id": 201,
      "name": "Santa Monica Pier",
      "category": "Landmark & Outdoors",
      "latitude": 34.0094,
      "longitude": -118.4973,
      "recommended_duration_min": 90,
      "visit_order": 1
    }
  ],
  "intent_data": {
    "preference_factors": {
      "factor_1": {"weight": 0.35, "label": "文化探索"},
      "factor_2": {"weight": 0.25, "label": "自然风光"},
      "factor_3": {"weight": 0.22, "label": "美食体验"},
      "factor_4": {"weight": 0.18, "label": "休闲购物"}
    },
    "transfer_weights": {
      "factor_1_alpha": 0.40,
      "factor_2_alpha": 0.30,
      "factor_3_alpha": 0.20,
      "factor_4_alpha": 0.10
    },
    "city_group_preference": {
      "cultural": 0.60,
      "nature": 0.20,
      "food": 0.15,
      "shopping": 0.05
    },
    "reliability_score": 0.72,
    "blend_weight_eta": 0.65
  },
  "generation_confidence": 0.78
}
```

**意图数据字段说明**（对应第四章）：

| 字段 | 对应论文概念 | 说明 |
|------|-------------|------|
| `preference_factors` | K=4维正交偏好因子 | 用户偏好被解耦为4个独立维度 |
| `transfer_weights` | 偏好迁移权重α_k | 各偏好维度从源城市到目标城市的迁移系数 |
| `city_group_preference` | 城市群体记忆向量m_g | 目标城市的群体偏好模式 |
| `reliability_score` | 可靠性权重ρ_g | 反映目标城市数据充分程度 |
| `blend_weight_eta` | 融合门控η | 个人偏好与群体偏好的融合比例 |

#### 3.2.5 DeepSeek LLM Agent（通用城市）

**调用条件**：目的城市不在上述数据集覆盖范围内

**Agent 工作流程**：

```
用户查询 + 用户偏好
        │
        ▼
┌─────────────────────┐
│  查询预处理          │
│  提取五元组 + 偏好   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Prompt构建          │
│  • 系统角色设定      │
│  • 用户偏好注入      │
│  • 查询条件格式化    │
│  • 输出JSON格式约束  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  DeepSeek API 调用   │
│  Model: deepseek-chat│
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  响应解析与校验      │
│  JSON → 标准路线格式 │
└────────┬────────────┘
         │
         ▼
   标准化路线结果
  （无intent_data）
```

**Prompt模板示例**：
```
你是一个专业的旅行规划助手。请根据以下用户信息和查询条件，生成一条个性化的旅行路线。

【用户偏好】
- 兴趣类别：{interested_categories}
- 出行风格：{travel_style}
- 同行人：{companion_type}
- 预算级别：{budget_level}

【查询条件】
- 目的城市：{destination_city}
- 出发时间：{start_time}
- 结束时间：{end_time}
- 期望途经点数：{num_stops}

【输出要求】
请以JSON格式输出，包含以下字段：
{
  "route": [
    {
      "name": "景点名称",
      "category": "类别",
      "latitude": 纬度,
      "longitude": 经度,
      "recommended_duration_min": 建议停留时长(分钟),
      "visit_order": 访问顺序,
      "description": "简要推荐理由"
    }
  ],
  "route_summary": "路线整体说明"
}
```

**返回数据格式**：
```json
{
  "algorithm": "DeepSeek-Agent",
  "city": "北京",
  "route": [
    {
      "poi_id": null,
      "name": "故宫博物院",
      "category": "Cultural & Historical",
      "latitude": 39.9163,
      "longitude": 116.3972,
      "recommended_duration_min": 180,
      "visit_order": 1,
      "description": "中国最大的古代宫殿建筑群"
    }
  ],
  "intent_data": null,
  "route_summary": "这条路线以北京核心文化景点为主...",
  "generation_confidence": null
}
```

#### 3.2.6 Mock/Real 模式切换

系统通过全局配置 `USE_MOCK_DATA` 控制数据来源：

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| **Mock模式** (`True`) | 从mock_routes表读取预设数据返回 | 答辩演示、前端开发调试 |
| **Real模式** (`False`) | 实际调用算法推理服务或DeepSeek API | 真实环境运行 |

**注意**：Mock/Real开关仅影响EKD-Trip和CrossCityLLMCPR两个算法接口。DeepSeek LLM Agent始终进行实际API调用（因其不依赖本地算法服务）。

### 3.3 意图可视化模块（论文呼应核心）

本模块是TripManner区别于一般旅行规划系统的关键特色，通过可视化算法推理过程中的用户偏好意图，增强系统的可解释性和可信度。

#### 3.3.1 单城市意图可视化（EKD-Trip场景）

当系统调用EKD-Trip算法时，在路线结果旁展示以下可视化内容：

**① Travel Mode 分类展示**
- 以图标+文字标签展示识别出的travel mode类型
- 四种模式对应四种不同的视觉符号：
  - Approaching (接近)：↘ 渐近箭头，配绿色
  - Moving Away (远离)：↗ 远离箭头，配橙色
  - U-turn (U型)：⤺ U型曲线，配蓝色
  - Irregular (不规则)：✳ 散点符号，配灰色
- 显示分类置信度百分比

**② 距离变化曲线图**
- X轴：访问POI顺序（第1个 → 第N个）
- Y轴：当前POI到目的地的距离（km）
- 折线图展示距离变化趋势，直观体现travel mode的含义
- 使用ECharts line chart组件实现

**③ 模式说明文字**
- 简要解释当前travel mode的含义
- 例："系统识别到您的出行意图为【接近模式】：您倾向于沿途逐步接近最终目的地，不绕远路。"

#### 3.3.2 跨城市意图可视化（CrossCityLLMCPR场景）

当系统调用CrossCityLLMCPR算法时，展示以下可视化内容：

**① 4维偏好因子雷达图**
- ECharts radar chart
- 4个轴分别对应K=4个偏好维度（文化探索/自然风光/美食体验/休闲购物）
- 显示各维度的权重值
- 颜色区分用户个人偏好 vs 城市群体偏好的叠加

**② 偏好迁移权重可视化**
- Sankey图或带权重的箭头图
- 左侧：源城市的4个偏好因子
- 右侧：目标城市适配后的4个偏好因子
- 连线粗细表示迁移权重α_k的大小
- 直观展示"哪些偏好被更多地迁移到了新城市"

**③ 城市群体偏好饼图/环形图**
- 展示目标城市的群体偏好分布
- 配合可靠性得分ρ_g显示数据充分程度
- 例：ρ_g=0.72 → "目标城市数据可靠性：72%"

**④ 个人-群体融合比例**
- 显示η值（个人偏好权重）和1-η值（群体偏好权重）
- 可视化为进度条或双色饼图
- 例：η=0.65 → "路线中65%基于您的个人偏好，35%参考了当地热门趋势"

#### 3.3.3 通用城市场景

当系统调用DeepSeek LLM Agent时，**不显示意图可视化面板**（LLM不产出意图推断数据），仅展示路线规划结果和LLM的文字说明。

### 3.4 地图可视化模块

基于Leaflet + OpenStreetMap实现交互式地图展示。

**功能清单**：
| 功能 | 描述 |
|------|------|
| 路线绘制 | 在地图上用折线连接各POI，带方向箭头 |
| POI标记 | 每个推荐POI用编号标记显示在地图上 |
| POI详情弹窗 | 点击POI标记弹出名称、类别、推荐停留时长等信息 |
| 起终点高亮 | 起点（绿色）和终点（红色）用特殊图标标注 |
| 自动视窗适配 | 地图自动缩放至包含所有POI的最佳视窗 |
| 缩放/平移 | 支持鼠标滚轮缩放和拖拽平移 |

### 3.5 对话交互模块

参考苍穹杯TourGuide的对话式交互设计，提供自然语言旅行规划体验。本模块的两大核心特性为**引导式对话补全**和**流式输出与动态路线渲染**。

**功能清单**：
| 功能 | 描述 |
|------|------|
| 自然语言输入 | 用户用自然语言描述旅行需求 |
| 引导式对话补全 | 当用户输入缺少五元组必要字段时，系统逐步引导追问 |
| 流式文本输出 | 路线规划结果以SSE流式推送，前端逐字/逐句渲染 |
| 动态路线绘制 | 流式输出过程中，地图上同步逐步添加POI标记和路线连线 |
| 多轮对话 | 支持追问和路线调整 |
| 对话历史 | 持久化存储对话记录，支持历史对话恢复 |
| 结构化表单 | 同时支持表单式精确输入作为备选（跳过引导流程） |

#### 3.5.1 引导式对话补全

用户的自然语言输入往往不完整，系统通过DeepSeek LLM解析用户输入，提取已有字段并识别缺失字段，然后以友好的自然语言追问方式引导用户补全。

**五元组字段及引导策略**：

| 字段 | 是否必填 | 缺失时引导话术示例 |
|------|---------|-------------------|
| `destination_city` | 必填 | "请问您想去哪个城市旅行呢？" |
| `start_time` | 必填 | "您计划什么时候出发？比如上午9点" |
| `end_time` | 必填 | "大概玩到几点结束呢？" |
| `num_stops` | 可选（默认5） | "您希望途经几个景点？默认为您安排5个" |
| `departure_city` | 跨城市必填 | "您是从哪个城市出发的呢？" |

**引导流程**：

```
用户输入自然语言
      │
      ▼
┌──────────────────────────┐
│ DeepSeek解析：提取已有字段 │
│ 输出：已填字段 + 缺失字段  │
└────────────┬─────────────┘
             │
      ┌──────┴──────┐
      │ 缺失字段？   │
      └──────┬──────┘
        是   │   否
      ┌──────┴──────────────────┐
      ▼                         ▼
┌──────────────┐     ┌──────────────────┐
│ 生成引导追问  │     │ 五元组完整        │
│ (针对下一个   │     │ → 进入路由决策引擎│
│  缺失字段)    │     └──────────────────┘
└──────┬───────┘
       │
       ▼
  等待用户回答 → 合并已有信息 → 重新检查完整性（循环）
```

**LLM解析Prompt模板**：
```
你是一个旅行查询解析助手。请从用户的对话中提取以下字段，未提及的字段标记为null：
- destination_city: 目的城市
- departure_city: 出发城市（若为同城旅行则与目的城市相同）
- start_time: 出发时间
- end_time: 结束时间
- num_stops: 期望途经点数

【历史对话】
{conversation_history}

【当前用户输入】
{user_message}

请以JSON格式输出提取结果，并列出仍然缺失的字段。若缺失字段，请用友好的中文生成一句追问。
```

**引导对话示例**：
```
用户: 我想去东京玩
系统: 好的！东京是个很棒的选择~ 🗼
      请问您计划什么时候出发，大概玩到几点呢？比如"上午9点到晚上6点"
用户: 明天上午9点出发，玩一整天吧
系统: 收到！那就安排到晚上6点左右。您希望途经几个景点呢？默认为您安排5个。
用户: 5个就好
系统: [五元组完整] → [识别为单城市-Tokyo] → [调用EKD-Trip]
      [流式输出路线结果 + 动态绘制地图路线 + 意图可视化面板]
```

#### 3.5.2 流式输出与动态路线渲染

路线规划结果采用**Server-Sent Events (SSE)** 流式推送至前端，实现逐步输出的打字机效果，同时地图上同步动态绘制路线。

**流式输出架构**：

```
后端 (FastAPI)                          前端 (Vue 3)
┌────────────────┐                    ┌────────────────────────┐
│                │   SSE Stream       │                        │
│  算法/LLM调用  │ ──text/event──→   │  EventSource监听       │
│       │        │   stream           │       │                │
│       ▼        │                    │       ▼                │
│  逐POI封装事件 │                    │  ① 对话区：逐字渲染文本 │
│  • poi_added   │                    │  ② 地图区：逐步添加POI  │
│  • route_text  │                    │  ③ 意图区：最后渲染图表  │
│  • intent_data │                    │                        │
│  • done        │                    │                        │
└────────────────┘                    └────────────────────────┘
```

**SSE事件类型定义**：

| 事件类型 | 触发时机 | 数据内容 | 前端行为 |
|---------|---------|---------|---------|
| `thinking` | 开始处理 | `{"status": "analyzing"}` | 显示"正在分析您的需求..."加载提示 |
| `guide_question` | 需要引导追问 | `{"text": "请问您...", "missing_fields": [...]}` | 对话区显示追问文本 |
| `route_text` | 路线文本片段 | `{"delta": "为您规划了东京一日游..."}` | 对话区逐字追加渲染（打字机效果） |
| `poi_added` | 新增一个POI | `{"poi": {name, lat, lng, order, ...}}` | 地图上添加POI标记 + 延伸路线连线 |
| `intent_data` | 意图数据就绪 | `{"travel_mode": ..., ...}` 或 `{"preference_factors": ...}` | 渲染意图可视化面板 |
| `done` | 输出完成 | `{"plan_id": 42}` | 结束加载状态，保存对话记录 |
| `error` | 出错 | `{"message": "..."}` | 显示错误提示 |

**前端动态渲染时序**：

```
时间轴 ──────────────────────────────────────────────────→

[thinking]
  对话区: "🔍 正在分析您的需求..."

[route_text delta=①]
  对话区: "为您规划了东京"  ← 逐字出现

[route_text delta=②]
  对话区: "为您规划了东京一日游路线！共5个景点。"

[poi_added #1 浅草寺]
  对话区: "第1站：浅草寺 — 东京最古老的寺庙..."  ← 逐字出现
  地图区: 📍 浅草寺标记出现（带弹入动画）

[poi_added #2 上野公园]
  对话区: "第2站：上野公园 — 赏樱胜地..."
  地图区: 📍 上野公园标记出现 + 浅草寺→上野的路线连线（带绘制动画）

  ... 逐个POI ...

[poi_added #5 东京晴空塔]
  对话区: "第5站：东京晴空塔 — 全城地标..."
  地图区: 📍 完整路线绘制完毕

[intent_data]
  意图面板: 淡入显示Travel Mode图标 + 距离变化曲线 + 说明文字

[done]
  加载状态结束，对话记录保存
```

**动态路线绘制动画规格**：
| 动画元素 | 效果 | 时长 |
|---------|------|------|
| POI标记出现 | 从小到大弹入（ease-out） | 300ms |
| 路线连线绘制 | 虚线→实线逐步绘制 | 500ms |
| 意图面板出现 | 整体淡入（fade-in） | 400ms |
| 地图视窗调整 | 平滑flyTo包含新POI | 600ms |

### 3.6 数据管理模块

**功能清单**：
| 功能 | 描述 |
|------|------|
| POI数据管理 | 存储数据集城市的POI信息（名称、类别、经纬度、热度） |
| Mock数据管理 | 管理预设的mock路线数据 |
| 用户签到历史 | 存储模拟的用户签到记录（跨城市算法需要） |
| 系统配置管理 | Mock/Real开关及其他系统参数 |

---

## 4 非功能性需求

| 需求维度 | 要求 |
|---------|------|
| **响应时间** | 页面加载 < 3s；Mock模式首个SSE事件 < 300ms；LLM Agent首个SSE事件 < 2s |
| **流式体验** | 文本流式输出延迟 < 100ms/token；POI标记动态添加间隔300-800ms（模拟思考节奏） |
| **可用性** | 演示环境稳定可用，支持答辩现场流畅演示 |
| **可维护性** | 代码结构清晰，前后端分离，模块化设计 |
| **可扩展性** | 预留算法接口，未来可接入真实算法服务 |
| **安全性** | 用户密码BCrypt加密存储；基于数据库直接校验的认证机制；API Key不硬编码在前端 |
| **兼容性** | 支持Chrome、Firefox、Edge等主流浏览器；SSE需兼容EventSource API |

---

## 5 数据库设计

### 5.1 ER图概览

```
┌─────────┐       ┌──────────┐       ┌──────────┐
│  users   │──1:N──│  routes   │       │   pois   │
│          │       │          │       │          │
└─────┬────┘       └──────────┘       └──────────┘
      │
      │1:N
      ▼
┌──────────┐       ┌──────────────┐
│  dialogs  │       │  mock_routes  │
│          │       │              │
└──────────┘       └──────────────┘
```

### 5.2 表结构

#### users 表
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | 用户ID |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| `password_hash` | VARCHAR(255) | NOT NULL | BCrypt加密密码 |
| `nickname` | VARCHAR(50) | | 昵称 |
| `avatar_url` | VARCHAR(255) | | 头像URL |
| `preferences` | JSON | | 用户偏好（JSON格式） |
| `created_at` | DATETIME | DEFAULT NOW() | 创建时间 |
| `updated_at` | DATETIME | ON UPDATE NOW() | 更新时间 |

#### pois 表
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | POI ID |
| `name` | VARCHAR(200) | NOT NULL | POI名称 |
| `category` | VARCHAR(100) | | POI类别 |
| `city` | VARCHAR(100) | NOT NULL, INDEX | 所在城市 |
| `latitude` | DECIMAL(10,7) | NOT NULL | 纬度（WGS84） |
| `longitude` | DECIMAL(10,7) | NOT NULL | 经度（WGS84） |
| `popularity` | FLOAT | DEFAULT 0 | 热度分数 |
| `description` | TEXT | | POI描述 |

#### routes 表
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | 路线记录ID |
| `user_id` | INT | FK → users.id, INDEX | 用户ID |
| `query_input` | JSON | NOT NULL | 原始查询输入 |
| `algorithm_used` | ENUM('EKD-Trip','CrossCityLLMCPR','DeepSeek-Agent') | NOT NULL | 使用的算法 |
| `route_result` | JSON | NOT NULL | 路线结果（完整JSON） |
| `intent_data` | JSON | | 意图可视化数据 |
| `is_mock` | BOOLEAN | DEFAULT FALSE | 是否来自mock数据 |
| `created_at` | DATETIME | DEFAULT NOW() | 创建时间 |

#### dialogs 表
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | 对话ID |
| `user_id` | INT | FK → users.id, INDEX | 用户ID |
| `title` | VARCHAR(200) | | 对话标题（自动生成） |
| `messages` | JSON | | 消息列表 |
| `created_at` | DATETIME | DEFAULT NOW() | 创建时间 |
| `updated_at` | DATETIME | ON UPDATE NOW() | 更新时间 |

#### mock_routes 表
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | Mock数据ID |
| `city` | VARCHAR(100) | NOT NULL, INDEX | 城市 |
| `scenario_name` | VARCHAR(200) | NOT NULL | 场景名称（如"Tokyo一日游"） |
| `algorithm_type` | ENUM('EKD-Trip','CrossCityLLMCPR') | NOT NULL | 算法类型 |
| `query_input` | JSON | NOT NULL | 模拟查询输入 |
| `route_result` | JSON | NOT NULL | 预设路线结果 |
| `intent_data` | JSON | NOT NULL | 预设意图数据 |

#### user_checkins 表（跨城市算法所需的用户签到历史）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | 签到记录ID |
| `user_id` | INT | FK → users.id, INDEX | 用户ID |
| `poi_id` | INT | FK → pois.id | POI ID |
| `city` | VARCHAR(100) | INDEX | 签到城市 |
| `checkin_time` | DATETIME | | 签到时间 |

---

## 6 API设计

### 6.1 API概览

**Base URL**: `http://localhost:8000/api`

| 模块 | 方法 | 路径 | 描述 |
|------|------|------|------|
| **认证** | POST | `/auth/register` | 用户注册 |
| | POST | `/auth/login` | 用户登录 |
| **用户** | GET | `/user/profile` | 获取用户信息 |
| | PUT | `/user/profile` | 更新用户信息 |
| | PUT | `/user/preferences` | 更新用户偏好 |
| **路线规划** | POST | `/plan/route` | 核心路线规划（自动路由） |
| | GET | `/plan/history` | 获取历史规划列表 |
| | GET | `/plan/{id}` | 获取单条规划详情 |
| **对话** | POST | `/chat/message` | 发送对话消息（SSE流式响应） |
| | GET | `/chat/dialogs` | 获取对话列表 |
| | GET | `/chat/dialogs/{id}` | 获取单个对话详情 |
| **系统配置** | GET | `/config/mock-status` | 获取Mock开关状态 |
| | PUT | `/config/mock-status` | 切换Mock/Real模式 |
| | GET | `/config/supported-cities` | 获取各算法支持的城市列表 |

### 6.2 核心API详细设计

#### POST `/api/plan/route` — 核心路线规划

**Request Body**:
```json
{
  "query_text": "我想去东京玩一天，从早上9点到晚上6点，想去5个景点",
  "structured_query": {
    "departure_city": "Tokyo",
    "destination_city": "Tokyo",
    "start_time": "2026-05-01 09:00",
    "end_time": "2026-05-01 18:00",
    "num_stops": 5
  },
  "source_city_for_cross": null
}
```

> 注：`query_text` 和 `structured_query` 二选一。若提供 `query_text`，后端通过DeepSeek解析为结构化查询；若直接提供 `structured_query`，则跳过解析步骤。

**Response Body** (统一格式):
```json
{
  "success": true,
  "data": {
    "plan_id": 42,
    "algorithm": "EKD-Trip",
    "city": "Tokyo",
    "is_mock": true,
    "route": [...],
    "intent_data": {...},
    "route_summary": "...",
    "generation_confidence": 0.85
  }
}
```

#### POST `/api/chat/message` — 对话消息（SSE流式响应）

**Request Body**:
```json
{
  "dialog_id": 1,
  "message": "我想去东京玩"
}
```

**Response**: `Content-Type: text/event-stream`

每个SSE事件格式为 `event: <type>\ndata: <json>\n\n`，示例流：

```
event: thinking
data: {"status": "analyzing", "text": "正在分析您的需求..."}

event: guide_question
data: {"text": "好的！东京是个很棒的选择~ 请问您计划什么时候出发，大概玩到几点呢？", "parsed_fields": {"destination_city": "Tokyo"}, "missing_fields": ["start_time", "end_time", "num_stops"]}
```

当用户补全信息后再次发送消息，流式返回路线结果：

```
event: thinking
data: {"status": "planning", "text": "正在为您规划路线...", "algorithm": "EKD-Trip"}

event: route_text
data: {"delta": "为您规划了东京一日游路线！共5个景点。\n\n"}

event: poi_added
data: {"poi": {"poi_id": 1001, "name": "皇居", "category": "Historical Site", "latitude": 35.6852, "longitude": 139.7528, "recommended_duration_min": 60, "visit_order": 1}}

event: route_text
data: {"delta": "**第1站：皇居 (Imperial Palace)**\n日本天皇居所，感受皇家庭院的宁静...\n建议停留：60分钟\n\n"}

event: poi_added
data: {"poi": {"poi_id": 1002, "name": "浅草寺", "category": "Temple & Shrine", "latitude": 35.7148, "longitude": 139.7967, "recommended_duration_min": 75, "visit_order": 2}}

event: route_text
data: {"delta": "**第2站：浅草寺 (Senso-ji)**\n东京最古老的寺庙...\n建议停留：75分钟\n\n"}

... (逐POI输出) ...

event: intent_data
data: {"travel_mode": "approaching", "travel_mode_confidence": 0.87, "distance_to_destination_curve": [5.8, 3.2, 2.8, 2.1, 0.3]}

event: route_text
data: {"delta": "\n📊 系统识别到您的出行意图为【接近模式】：您倾向于沿途逐步接近最终目的地。置信度：87%"}

event: done
data: {"plan_id": 42, "algorithm": "EKD-Trip", "is_mock": true}
```

---

## 7 Mock数据规格

### 7.1 单城市Mock数据（EKD-Trip）

为Glasgow、Osaka、Toronto、Tokyo每个城市准备**3条**预设路线，涵盖不同的travel mode类型。

#### 示例：Tokyo Mock Route #1 — "东京经典一日游（接近模式）"
```json
{
  "city": "Tokyo",
  "scenario_name": "东京经典一日游 - 接近模式",
  "algorithm_type": "EKD-Trip",
  "query_input": {
    "start_poi": "Tokyo Station",
    "end_poi": "Tokyo Skytree",
    "start_time": 9,
    "end_time": 18,
    "num_pois": 5
  },
  "route_result": {
    "route": [
      {"poi_id": 1001, "name": "皇居 (Imperial Palace)", "category": "Historical Site", "latitude": 35.6852, "longitude": 139.7528, "recommended_duration_min": 60, "visit_order": 1},
      {"poi_id": 1002, "name": "浅草寺 (Senso-ji)", "category": "Temple & Shrine", "latitude": 35.7148, "longitude": 139.7967, "recommended_duration_min": 75, "visit_order": 2},
      {"poi_id": 1003, "name": "上野公园 (Ueno Park)", "category": "Park & Nature", "latitude": 35.7146, "longitude": 139.7732, "recommended_duration_min": 60, "visit_order": 3},
      {"poi_id": 1004, "name": "秋叶原 (Akihabara)", "category": "Shopping & Entertainment", "latitude": 35.7023, "longitude": 139.7745, "recommended_duration_min": 45, "visit_order": 4},
      {"poi_id": 1005, "name": "东京晴空塔 (Tokyo Skytree)", "category": "Landmark", "latitude": 35.7101, "longitude": 139.8107, "recommended_duration_min": 60, "visit_order": 5}
    ]
  },
  "intent_data": {
    "travel_mode": "approaching",
    "travel_mode_confidence": 0.87,
    "distance_to_destination_curve": [5.8, 3.2, 2.8, 2.1, 0.3],
    "query_representation_similarity": 0.82
  }
}
```

#### 示例：Glasgow Mock Route #1 — "格拉斯哥半日游（U型模式）"
```json
{
  "city": "Glasgow",
  "scenario_name": "格拉斯哥半日游 - U型模式",
  "algorithm_type": "EKD-Trip",
  "query_input": {
    "start_poi": "Glasgow Central Station",
    "end_poi": "Glasgow Cathedral",
    "start_time": 10,
    "end_time": 15,
    "num_pois": 4
  },
  "route_result": {
    "route": [
      {"poi_id": 2001, "name": "Kelvingrove Art Gallery", "category": "Museum", "latitude": 55.8687, "longitude": -4.2903, "recommended_duration_min": 60, "visit_order": 1},
      {"poi_id": 2002, "name": "University of Glasgow", "category": "Historical Site", "latitude": 55.8722, "longitude": -4.2882, "recommended_duration_min": 30, "visit_order": 2},
      {"poi_id": 2003, "name": "Buchanan Street", "category": "Shopping", "latitude": 55.8609, "longitude": -4.2514, "recommended_duration_min": 45, "visit_order": 3},
      {"poi_id": 2004, "name": "Glasgow Cathedral", "category": "Historical Site", "latitude": 55.8628, "longitude": -4.2345, "recommended_duration_min": 40, "visit_order": 4}
    ]
  },
  "intent_data": {
    "travel_mode": "u_turn",
    "travel_mode_confidence": 0.79,
    "distance_to_destination_curve": [3.5, 3.8, 1.2, 0.2],
    "query_representation_similarity": 0.75
  }
}
```

### 7.2 跨城市Mock数据（CrossCityLLMCPR）

为New York→Los Angeles、New York→San Francisco、Los Angeles→San Francisco各准备**2条**路线。

#### 示例：NY→LA Mock Route #1 — "纽约用户的洛杉矶文化之旅"
```json
{
  "city": "Los Angeles",
  "scenario_name": "纽约用户的洛杉矶文化之旅",
  "algorithm_type": "CrossCityLLMCPR",
  "query_input": {
    "source_city": "New York",
    "target_city": "Los Angeles",
    "num_pois": 5,
    "start_time": 9,
    "end_time": 19
  },
  "route_result": {
    "route": [
      {"poi_id": 3001, "name": "Getty Center", "category": "Museum & Art", "latitude": 34.0780, "longitude": -118.4741, "recommended_duration_min": 120, "visit_order": 1},
      {"poi_id": 3002, "name": "Santa Monica Pier", "category": "Landmark & Outdoors", "latitude": 34.0094, "longitude": -118.4973, "recommended_duration_min": 90, "visit_order": 2},
      {"poi_id": 3003, "name": "The Broad", "category": "Museum & Art", "latitude": 34.0545, "longitude": -118.2503, "recommended_duration_min": 75, "visit_order": 3},
      {"poi_id": 3004, "name": "Grand Central Market", "category": "Food & Drink", "latitude": 34.0508, "longitude": -118.2492, "recommended_duration_min": 60, "visit_order": 4},
      {"poi_id": 3005, "name": "Griffith Observatory", "category": "Landmark & Nature", "latitude": 34.1184, "longitude": -118.3004, "recommended_duration_min": 90, "visit_order": 5}
    ]
  },
  "intent_data": {
    "preference_factors": {
      "factor_1": {"weight": 0.35, "label": "文化探索"},
      "factor_2": {"weight": 0.25, "label": "自然风光"},
      "factor_3": {"weight": 0.22, "label": "美食体验"},
      "factor_4": {"weight": 0.18, "label": "休闲购物"}
    },
    "transfer_weights": {
      "factor_1_alpha": 0.40,
      "factor_2_alpha": 0.30,
      "factor_3_alpha": 0.20,
      "factor_4_alpha": 0.10
    },
    "city_group_preference": {
      "cultural": 0.55,
      "nature": 0.25,
      "food": 0.12,
      "shopping": 0.08
    },
    "reliability_score": 0.72,
    "blend_weight_eta": 0.65
  }
}
```

### 7.3 Mock数据总览

| 算法 | 城市 | 路线数 | 涵盖Travel Mode / 偏好场景 |
|------|------|--------|---------------------------|
| EKD-Trip | Tokyo | 3 | approaching, u_turn, irregular |
| EKD-Trip | Osaka | 3 | approaching, moving_away, u_turn |
| EKD-Trip | Glasgow | 3 | u_turn, approaching, irregular |
| EKD-Trip | Toronto | 3 | approaching, moving_away, u_turn |
| CrossCityLLMCPR | NY→LA | 2 | 文化偏好迁移、自然偏好迁移 |
| CrossCityLLMCPR | NY→SF | 2 | 美食偏好迁移、综合偏好迁移 |
| CrossCityLLMCPR | LA→SF | 2 | 休闲偏好迁移、文化偏好迁移 |
| **合计** | | **18** | |

---

## 8 前端页面设计

### 8.1 页面列表

| 页面 | 路由 | 描述 |
|------|------|------|
| 登录页 | `/login` | 用户登录表单 |
| 注册页 | `/register` | 用户注册表单 |
| 主页（对话页） | `/` | 核心交互页面：对话 + 地图 + 意图可视化 |
| 偏好设置页 | `/settings` | 用户偏好配置 |
| 历史记录页 | `/history` | 查看历史路线规划 |
| 系统管理页 | `/admin` | Mock/Real开关、系统状态 |

### 8.2 主页布局（核心页面）

```
┌────────────────────────────────────────────────────────────────┐
│  TripManner                    [用户名]  [设置]  [退出]        │
├──────────┬──────────────────────────┬──────────────────────────┤
│          │                          │                          │
│  对话列表 │    对话区域（流式输出）    │    地图区域 (Leaflet)    │
│          │                          │                          │
│  ────── │  🤖 好的！东京是个很棒    │   [动态绘制路线 +        │
│  对话1   │  的选择~ 请问您计划什    │    逐步添加POI标记]      │
│  对话2   │  么时候出发？            │                          │
│  对话3   │                          │    📍1 → 📍2 → 📍3     │
│  ...     │  👤 明天9点到晚上6点     │         → 📍4 → 📍5     │
│          │                          │                          │
│          │  🤖 正在为您规划路线...   │                          │
│          │  ▌ (打字机光标)           │                          │
│          │                          │                          │
│          │  第1站：皇居 ← 逐字出现  │                          │
│          │  第2站：浅草寺 ...        │                          │
│          │                          │                          │
│          ├──────────────────────────┴──────────────────────────┤
│          │                                                     │
│          │         意图可视化面板 (路线输出完成后淡入)             │
│          │  ┌─────────────┬───────────────┬──────────────┐     │
│          │  │Travel Mode  │ 距离变化曲线   │  模式说明     │     │
│          │  │  图标+标签   │  ECharts折线图 │  文字解释     │     │
│          │  └─────────────┴───────────────┴──────────────┘     │
│          │  或                                                   │
│          │  ┌──────────┬────────────┬──────────┬────────────┐  │
│          │  │偏好雷达图 │偏好迁移图   │群体偏好  │融合比例    │  │
│          │  └──────────┴────────────┴──────────┴────────────┘  │
│          ├─────────────────────────────────────────────────────┤
│          │  ┌─────────────────────────────────┐  [发送]       │
│          │  │  请输入您的旅行需求...             │              │
│          │  └─────────────────────────────────┘              │
│          │  [算法: EKD-Trip ▼] [Mock ◉ / Real ○]             │
└──────────┴─────────────────────────────────────────────────────┘
```

**布局说明**：
- 左侧面板（约200px宽）：对话历史列表
- 右侧上方左半部分（约50%宽）：对话区域，支持流式文本渲染（打字机效果）
- 右侧上方右半部分（约50%宽）：Leaflet地图，支持动态路线绘制
- 右侧中部（约20%高度）：意图可视化面板（路线流式输出完成后淡入显示）
- 右侧底部：对话输入框 + 算法/Mock状态指示

### 8.3 意图可视化面板详细设计

**EKD-Trip场景面板**:
```
┌────────────────────────────────────────────────────────────┐
│ 📊 用户出行意图分析 (EKD-Trip)                              │
├──────────────┬─────────────────────┬───────────────────────┤
│              │                     │                       │
│  Travel Mode │   距离变化曲线       │  意图解读             │
│              │                     │                       │
│   ↘ 接近    │   5.8               │  系统识别到您的出行    │
│              │     ╲               │  意图为【接近模式】：  │
│  置信度:87% │      3.2            │  您倾向于沿途逐步      │
│              │        ╲  2.8       │  接近最终目的地，      │
│              │         ╲           │  不绕远路。           │
│              │          2.1        │                       │
│              │            ╲ 0.3    │  置信度：87%          │
│              │   ───────────────  │                       │
│              │   1  2  3  4  5    │                       │
│              │   (POI访问顺序)      │                       │
└──────────────┴─────────────────────┴───────────────────────┘
```

**CrossCityLLMCPR场景面板**:
```
┌──────────────────────────────────────────────────────────────┐
│ 📊 跨城市偏好意图分析 (CrossCityLLMCPR)                       │
├──────────────┬───────────────┬──────────────┬────────────────┤
│              │               │              │                │
│ 偏好因子雷达图│ 偏好迁移可视化 │ 城市群体偏好  │ 融合比例       │
│              │               │              │                │
│   文化 0.35  │ NY → LA       │  ◉ 文化 55%  │ ▓▓▓▓▓▓░░░░    │
│  ╱    ╲     │ ─α₁=0.4──→   │  ◉ 自然 25%  │  65% 个人      │
│ 购物    自然 │ ─α₂=0.3──→   │  ◉ 美食 12%  │  35% 群体      │
│  ╲    ╱     │ ─α₃=0.2──→   │  ◉ 购物 08%  │                │
│   美食 0.22  │ ─α₄=0.1──→   │              │  可靠性:72%    │
│              │               │              │                │
└──────────────┴───────────────┴──────────────┴────────────────┘
```

---

## 9 演示场景设计（答辩用）

### 场景1：单城市 — 东京一日游（引导对话 + Approaching Mode）

**操作步骤**：
1. 用户登录系统
2. 在对话框输入不完整需求："我想去东京玩"
3. 系统引导追问："请问您计划什么时候出发，大概玩到几点呢？"
4. 用户回答："明天上午9点到晚上6点，安排5个景点"
5. 系统五元组完整 → 识别为单城市Tokyo → 调用EKD-Trip（Mock模式）
6. **流式输出**：对话区逐字出现路线文本，地图上逐步添加POI标记和路线连线
7. **展示重点**：
   - 引导式对话补全演示
   - 流式输出的打字机效果 + 地图动态路线绘制
   - 意图面板显示"接近模式"图标 + 距离递减曲线

### 场景2：单城市 — 格拉斯哥半日游（U-turn Mode）

**操作步骤**：
1. 输入完整需求（无需引导）："Plan a half-day trip in Glasgow, from 10am to 3pm, 4 stops"
2. 系统调用EKD-Trip → Glasgow Mock → 流式输出路线
3. **展示重点**：
   - 意图面板显示"U型模式" — 距离先增后减的曲线
   - 对比场景1的接近模式，展示不同travel mode的差异
   - 流式输出过程中地图动态绘制路线

### 场景3：跨城市 — 纽约用户去洛杉矶（偏好迁移）

**操作步骤**：
1. 确保当前用户有纽约的签到历史数据（预置）
2. 输入："我在纽约住了很久，这次想去洛杉矶玩，帮我规划5个景点"
3. 系统识别为跨城市 NY→LA → 调用CrossCityLLMCPR（Mock模式）→ 流式输出
4. **展示重点**：
   - 4维偏好雷达图展示用户偏好分布
   - 偏好迁移图展示从NY到LA的迁移权重
   - 城市群体偏好饼图展示LA的群体偏好
   - 融合比例条展示个人vs群体偏好的融合

### 场景4：通用城市 — 北京旅行（LLM Agent + 实时流式）

**操作步骤**：
1. 输入："帮我规划一个北京3天2夜的行程，我喜欢历史文化和美食"
2. 系统识别北京不在数据集内 → 调用DeepSeek LLM Agent（真实API调用）
3. **展示重点**：
   - DeepSeek实时流式生成，打字机效果更明显（因为是真实LLM调用而非Mock）
   - 地图展示路线动态绘制，但**不显示**意图可视化面板
   - 对比说明：非数据集城市无法进行意图推断

### 场景5：Mock/Real 模式切换

**操作步骤**：
1. 进入系统管理页
2. 展示当前Mock模式状态
3. 切换为Real模式
4. 说明Real模式下会调用真实算法推理服务
5. 切回Mock模式继续演示

---

## 10 项目目录结构（建议）

```
tripPlanner/
├── PRD.md                      # 本PRD文档
├── frontend/                   # 前端项目
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.js        # 路由配置
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   ├── Register.vue
│   │   │   ├── Home.vue        # 主页（对话+地图+意图可视化）
│   │   │   ├── Settings.vue    # 偏好设置
│   │   │   ├── History.vue     # 历史记录
│   │   │   └── Admin.vue       # 系统管理
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatPanel.vue       # 对话面板
│   │   │   │   ├── ChatInput.vue       # 输入框
│   │   │   │   └── ChatHistory.vue     # 对话历史列表
│   │   │   ├── map/
│   │   │   │   └── MapView.vue         # Leaflet地图组件
│   │   │   ├── intent/
│   │   │   │   ├── IntentPanel.vue     # 意图可视化容器
│   │   │   │   ├── TravelModeViz.vue   # Travel Mode可视化(EKD-Trip)
│   │   │   │   ├── DistanceCurve.vue   # 距离变化曲线
│   │   │   │   ├── PreferenceRadar.vue # 偏好雷达图(CrossCity)
│   │   │   │   ├── TransferFlow.vue    # 偏好迁移可视化
│   │   │   │   └── CityPreference.vue  # 城市群体偏好
│   │   │   └── common/
│   │   │       ├── Navbar.vue
│   │   │       └── Loading.vue
│   │   ├── api/
│   │   │   ├── auth.js          # 认证API
│   │   │   ├── plan.js          # 路线规划API
│   │   │   ├── chat.js          # 对话API
│   │   │   └── config.js        # 系统配置API
│   │   ├── stores/
│   │   │   ├── user.js          # 用户状态(Pinia)
│   │   │   └── app.js           # 应用全局状态
│   │   └── utils/
│   │       └── request.js       # Axios封装
│   └── public/
│       └── index.html
│
├── backend/                    # 后端项目
│   ├── requirements.txt
│   ├── main.py                 # FastAPI入口
│   ├── config.py               # 配置（含USE_MOCK_DATA开关）
│   ├── database.py             # 数据库连接
│   ├── models/                 # SQLAlchemy ORM模型
│   │   ├── user.py
│   │   ├── poi.py
│   │   ├── route.py
│   │   ├── dialog.py
│   │   └── mock_route.py
│   ├── routers/                # API路由
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── plan.py
│   │   ├── chat.py
│   │   └── config.py
│   ├── services/               # 业务逻辑
│   │   ├── route_decision.py   # 路由决策引擎
│   │   ├── ekd_trip.py         # EKD-Trip算法接口
│   │   ├── cross_city.py       # CrossCityLLMCPR接口
│   │   ├── llm_agent.py        # DeepSeek LLM Agent
│   │   └── mock_data.py        # Mock数据服务
│   ├── schemas/                # Pydantic数据模型
│   │   ├── auth.py
│   │   ├── plan.py
│   │   └── chat.py
│   └── data/
│       └── mock/               # Mock数据JSON文件
│           ├── tokyo_routes.json
│           ├── osaka_routes.json
│           ├── glasgow_routes.json
│           ├── toronto_routes.json
│           ├── ny_la_routes.json
│           ├── ny_sf_routes.json
│           └── la_sf_routes.json
│
└── reference/                  # 参考材料（已有）
    ├── 可信可解释时空表征学习研究与实现_杨凯.pdf
    ├── 05_作品介绍文档.docx
    ├── 06_系统概述.docx
    ├── 数据库设计说明书.docx
    ├── 02_安装及配置文件.md
    └── 03_部署说明文档.md
```

---

## 11 开发里程碑

| 阶段 | 内容 | 产出 |
|------|------|------|
| **阶段1：后端基础** | FastAPI项目搭建、数据库建表、用户认证、基础API | 可运行的后端服务 |
| **阶段2：路线规划核心** | 路由决策引擎、Mock数据服务、DeepSeek Agent集成 | 核心规划接口可用 |
| **阶段3：前端基础** | Vue3项目搭建、页面路由、登录注册、对话UI | 基本前端框架 |
| **阶段4：地图与可视化** | Leaflet地图集成、ECharts意图可视化组件 | 完整的可视化展示 |
| **阶段5：联调与演示** | 前后端联调、Mock数据填充、演示场景验证 | 可演示的完整系统 |

---

## 附录A：与论文章节的对应关系

| 系统模块/功能 | 对应论文章节 | 具体对应内容 |
|-------------|------------|-------------|
| EKD-Trip算法调用 | 第三章 | 基于知识蒸馏与显式意图增强的旅行路线推荐 |
| Travel Mode可视化 | 第三章 3.3节 | 四种出行模式分类（approaching/moving_away/u_turn/irregular） |
| 距离变化曲线 | 第三章 3.3节 | 用户到目的地的距离序列 |
| CrossCityLLMCPR算法调用 | 第四章 | 融合多维用户偏好意图的跨城市旅行路线推荐 |
| 4维偏好雷达图 | 第四章 4.2节 | K=4维正交偏好因子解耦 |
| 偏好迁移可视化 | 第四章 4.3节 | 自适应偏好迁移权重α_k |
| 城市群体偏好 | 第四章 4.3节 | EMA城市群体记忆向量m_g |
| 可靠性权重 | 第四章 4.3节 | 可靠性权重ρ_g = n_g/(n_g+κ) |
| 融合比例展示 | 第四章 4.3节 | 可学习门控η |

## 附录B：与苍穹杯TourGuide的差异对比

| 维度 | TourGuide (苍穹杯) | TripManner (毕业论文) |
|------|--------------------|--------------------|
| **后端架构** | SpringBoot + FastAPI | 纯FastAPI（简化） |
| **地图组件** | KQGIS + Leaflet | 纯Leaflet + OSM |
| **路线算法** | 纯LLM生成 | 三路由：EKD-Trip / CrossCity / LLM |
| **意图可视化** | 无 | Travel Mode、偏好雷达图、迁移图等 |
| **对话交互** | 一次性输入完整需求 | 引导式对话补全 + SSE流式输出 + 地图动态路线绘制 |
| **Mock支持** | 无 | Mock/Real双模式开关 |
| **论文关联** | 无 | 深度关联第三、四章算法 |
| **LLM选择** | 未明确 | DeepSeek API |
| **数据库** | MySQL（苍穹杯库） | MySQL（简化重构） |
