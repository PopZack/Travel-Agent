# Travel Agent ✈️

旅行智能体 — 从自然语言需求到行程规划、报价确认、真实预订下单的完整闭环。

## 能力

- 🗣️ **自然语言意图理解**：「11 月初带爸妈去京都 4 天，预算 1.5 万，喜欢文化少走路」
- 🔍 **实时数据检索**：机票（Amadeus）、酒店、景点餐厅（Google Places）、天气、路线、汇率
- 📅 **智能行程编排**：按天排日程，考虑开放时间、交通时长、体力、预算
- 🔎 **第二视角审查**：自动检查赶路过多/景点关门/预算超支，不通过自动重排（最多 3 轮）
- ✅ **人工确认下单**：报价展示 → 用户显式确认 → 下单（价格变动 >5% 触发二次确认）
- 🧠 **用户记忆**：记住偏好与历史行程

## 架构

```
用户输入 ──▶ Streamlit UI ──▶ LangGraph 状态机 ──▶ 工具层 ──▶ 外部 API
                  ▲                  │
                  │   (interrupt)    ▼
                  └── 待确认/结果 ── 预订节点
```

LangGraph 节点：`parse_intent → research → plan → critique ⇄ present → await_confirm → book → END`

- **parse_intent**：LLM 抽取结构化意图
- **research**：并行调 5 个工具（asyncio.gather）
- **plan**：LLM 编排按天行程
- **critique**：独立 LLM 审查，不通过回 plan
- **present**：生成报价
- **book**：`interrupt` 暂停等用户确认，resume 后调 Amadeus 下单

## 快速开始

### 1. 安装依赖

```bash
# 推荐用 uv（快）
uv sync

# 或用 pip
pip install -e ".[dev]"
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env 填入真实 key
```

需要的 key：
| Key | 用途 | 申请地址 |
|-----|------|---------|
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | LLM（火山方舟，OpenAI 兼容） | https://www.volcengine.com/product/ark |
| `AMADEUS_CLIENT_ID/SECRET` | 机票酒店 | https://developers.amadeus.com |
| `GOOGLE_PLACES_API_KEY` | 景点餐厅 | https://console.cloud.google.com |
| `OPENWEATHER_API_KEY` | 天气 | https://openweathermap.org/api |
| `EXCHANGE_RATE_API_KEY` | 汇率（可选） | https://www.exchangerate-api.com |

### 3. 运行

```bash
streamlit run app/streamlit_app.py
```

浏览器打开 http://localhost:8501，输入旅行需求即可。

### 4. 测试

```bash
pytest
```

## 安全说明

- **默认 `AMADEUS_ENV=test`**：下单只返回模拟 PNR，不真实扣款。切到 `prod` 需自行申请 Amadeus 生产授权。
- **全程 human-in-the-loop**：每笔下单前必须在界面上显式确认。
- **API key 走 `.env`**，已 in `.gitignore`，不进 git。

## 项目结构

```
src/travel_agent/
├── config.py          # 配置加载
├── state.py           # LangGraph 状态
├── graph.py           # 状态图构建
├── nodes/             # 6 个节点
├── tools/             # 6 个工具（Amadeus/Places/Weather/Routing/Exchange/Visa）
├── models/            # pydantic 数据模型
├── memory/            # SQLite 记忆
└── cache.py           # TTL 缓存
app/streamlit_app.py   # Web UI
tests/                 # 单测
```

## 技术栈

| 层 | 选型 |
|----|------|
| Agent 框架 | LangGraph |
| LLM | 火山方舟（OpenAI 兼容接口），默认模型由 .env 的 LLM_MODEL 指定 |
| 数据源 | Amadeus · Google Places · OpenWeather · OSRM · exchangerate |
| 存储 | SQLite（记忆）+ 内存缓存（MVP） |
| 界面 | Streamlit |
| 包管理 | uv / hatch |

## 后续扩展

- [ ] FastAPI 后端（供移动端/第三方集成）
- [ ] Redis 缓存
- [ ] 自建 OSRM 容器（docker-compose 已预留）
- [ ] 多用户登录
- [ ] 行中助手（改签、附近推荐）

## License

Apache-2.0
