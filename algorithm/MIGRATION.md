# 算法集成迁移指南 (Phase 3)

本文档说明如何在具备 GPU 的真实环境下启用 EKD-Trip 与 CrossTrip 算法的真实推理。

> 默认情况下，本仓库中的两个 wrapper 都会以 **graceful degradation** 模式运行：
> 当 `torch` / `mamba_ssm` / 模型权重 / 数据集任一缺失时，`is_available()` 返回 `False`，
> 后端 `/chat/message` SSE 接口会自动回退到 mock JSON 数据流。
> 因此当前的开发机（无 GPU）仍然可以正常运行所有联调与 Demo 录制工作。

---

## 1. 总体架构

```
backend/
├── services/
│   ├── ekd_trip.py            # EKD-Trip wrapper (新)
│   ├── cross_city.py          # CrossTrip wrapper (新)
│   └── llm_agent.py           # DeepSeek 接入 (已有)
└── routers/
    └── chat.py                # 调度: 城市路由 + 真实/Mock 回退
```

调度逻辑（见 `chat.py`）：

| 场景 | 条件 | 流式生成器 |
| --- | --- | --- |
| LLM-only | `algorithm == "llm_only"` | `_stream_deepseek_route` |
| 真实算法 | `algorithm in ("ekd_trip","cross_city")` 且 `USE_REAL_ALGORITHMS=True` 且 `wrapper.is_available()` | `_stream_real_algorithm`（失败自动回退到 mock） |
| Mock | 非以上 + `USE_MOCK_DATA=True` | `_stream_mock_route` |
| 兜底 | 其它 | DeepSeek |

---

## 2. 环境需求

GPU 机器（建议 Linux/CUDA 11.8+）需安装：

```bash
# 共同依赖
pip install -r backend/requirements.txt

# EKD-Trip / CrossTrip 真实推理依赖
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cu118
pip install mamba-ssm==1.2.0
pip install causal-conv1d==1.2.0
pip install einops
```

> Windows + Python 3.13 当前 **不支持** `mamba_ssm`（依赖 CUDA 编译扩展），
> 这是设计上设置 `is_available()` 守卫的核心动机。

---

## 3. 模型权重摆放

权重不应入仓库（已在 `.gitignore` 屏蔽 `*.pt *.pth *.ckpt *.bin *.xhr`）。
按下表放置后，在 `backend/.env` 中填入绝对路径即可：

| 算法 | 期望文件 | .env key |
| --- | --- | --- |
| EKD-Trip | `algorithm/EKDTrip/saved_models/model_best.pt`（举例） | `EKDTRIP_CHECKPOINT` |
| CrossTrip | `algorithm/CrossTrip/Yelp/model_save_new/model_best_f1.xhr` | `CROSSTRIP_CHECKPOINT` |

`backend/.env` 示例：

```dotenv
USE_MOCK_DATA=False
USE_REAL_ALGORITHMS=True
EKDTRIP_CHECKPOINT=/abs/path/to/algorithm/EKDTrip/saved_models/model_best.pt
CROSSTRIP_CHECKPOINT=/abs/path/to/algorithm/CrossTrip/Yelp/model_save_new/model_best_f1.xhr
```

---

## 4. EKD-Trip 数据依赖

Wrapper 在第一次调用 `predict_route(city=...)` 时会从以下位置加载：

```
algorithm/EKDTrip/dataset/vocab/vocab_to_int_<slug>.pkl
algorithm/EKDTrip/dataset/origin_data/poi-<slug>.csv
algorithm/EKDTrip/dataset/data/<slug>_max_distance.json    (可选)
algorithm/EKDTrip/dataset/data/<slug>_poi_id_latlon.json   (可选)
```

支持的 slug 在 `services/ekd_trip.py::CITY_SLUG_MAP`：

| 用户输入 | EKD-Trip slug |
| --- | --- |
| Tokyo / 东京 | `TKY_split200` |
| Osaka / 大阪 | `Osak` |
| Glasgow / 格拉斯哥 | `Glas` |
| Toronto / 多伦多 | `Toro` |

如训练新城市，仅需新增 vocab + csv，并在 `CITY_SLUG_MAP` 添加映射。

---

## 5. CrossTrip 数据依赖

Wrapper 期望以下文件至少一份存在：

```
algorithm/CrossTrip/Yelp/poi_id.pkl          # business_id <-> int 映射
algorithm/CrossTrip/Yelp/poi_coord.pkl       # business_id -> (lat, lon)
algorithm/CrossTrip/Yelp/yelp_business_cache.json  # 可选: 名称/类别
```

`Foursquare` 子目录同理。当前训练只覆盖了三对城市（见
`services/cross_city.py::SUPPORTED_PAIRS`），其它城市对会在
`predict_route` 中抛出 `RuntimeError`，由 chat router 捕获后回退到 mock。

> **重要**：CrossTrip 完整推理本应使用 `TravelDatasetV2` 重建用户历史；
> wrapper 出于"快速对接"目的，在没有 history 数据时使用零向量与
> 随机 popularity，本质上等价于"新用户冷启动"。这样得到的结果在
> Demo 中可用，但论文级评测仍应跑 `code/main.py --mode test`。

---

## 6. 烟雾测试

安装好依赖与权重后，从 `backend/` 目录执行：

```bash
# 1) 检查 wrapper 自报可用
python - <<'PY'
from services import ekd_trip, cross_city
print("EKD-Trip available :", ekd_trip.is_available())
print("  reason:", ekd_trip.unavailable_reason())
print("CrossTrip available:", cross_city.is_available())
print("  reason:", cross_city.unavailable_reason())
PY

# 2) 端到端调用
python - <<'PY'
from services.ekd_trip import predict_route
result = predict_route(
    destination_city="Tokyo",
    start_poi="Imperial Palace",
    end_poi="Tokyo Skytree",
    num_pois=5,
)
import json; print(json.dumps(result, ensure_ascii=False, indent=2))
PY
```

或者直接命中 SSE 端点：

```bash
curl -N -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"我想在东京玩一天",
    "context":{
      "destination_city":"Tokyo",
      "start_poi":"Imperial Palace",
      "end_poi":"Tokyo Skytree",
      "start_time":9,
      "end_time":18,
      "num_stops":5
    }
  }'
```

---

## 7. 已知限制与注意事项

1. **EKD-Trip 输入构造简化**：完整训练管线提供 trend/time/distance 张量，wrapper 用零张量替代，因此真实场景下输出质量略低于论文报告值。
2. **CrossTrip 需要训练数据集**：未提供 `poi_id.pkl` 时 wrapper 直接报告不可用。
3. **多用户/多设备并发**：wrapper 使用模块级单例并 `eval()` 锁定模型，多请求并发安全；但首请求会触发模型加载（约 10–30s）。
4. **回退策略可见性**：当真实算法触发回退时，前端会先收到 `event: error` 然后切换到 mock 流；UI 应忽略 `fallback=true` 的 error，避免出现红色提示。当前 router 已在内部吞掉该事件，仅前端显示完整 mock 路线。
