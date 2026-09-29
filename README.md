# Travel Agent ✈️

旅行智能体 — FastAPI + LangGraph Agent Loop，从自然语言对话到行程规划、修改、保存的完整闭环。

## 能力

- 🗣️ **自然语言对话**：闲聊、问推荐、问景点，Agent 自然回应
- 🧠 **意图理解**：自动区分闲聊 / 规划行程 / 修改行程 / 问天气
- ❓ **主动追问**：信息不完整时返回结构化选择选项（目的地/天数/预算/人数）
- 🔍 **实时数据检索**：景点/餐厅（高德+Google Places）、天气、汇率、签证
- 📅 **智能行程编排**：按天排日程，考虑天气、开放时间、预算
- 🔎 **行程审查**：自动检查赶路过多/预算超支，不通过自动重排
- ✏️ **Re-planning**：用户说"第三天删掉迪士尼"即可修改已有行程
- 💾 **行程保存**：SQLite 持久化，支持历史查询
- 🧠 **对话记忆**：多轮对话上下文，继承目的地等信息

## 架构

```
用户 → FastAPI → LangGraph → Travel Agent
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
         LLM        Tools        Memory
          │           │           │
       理解/决策     执行        SQLite
```

### LangGraph 节点流程

```
START → understand → check_info
                        ↓
                  信息完整？
                  /       \
                No         Yes
                ↓           ↓
           ask_user     call_tools → (travel_plan → plan_trip / modify_plan → replan)
                ↓                       ↓
              END                  validate_plan
                                     ↓
                                   合格？
                                  /       \
                                No         Yes
                                ↓           ↓
                              replan    final_response → END
```

### 各节点职责

| 节点 | 职责 |
|------|------|
| understand_request | LLM 从用户消息+对话历史提取 intent + slot |
| check_information | 检查必填字段，设 missing_fields |
| ask_user | 生成结构化选择式追问 |
| call_tools | 并行调景点/餐厅/天气/汇率/签证工具 |
| plan_trip | LLM 生成结构化行程 |
| validate_plan | 检查行程合理性，不通过回 replan |
| replan | 读取当前行程，根据用户请求修改 |
| final_response | 有行程→总结；无行程→闲聊回复 |

## 快速开始

### 1. 安装依赖

```bash
uv sync --extra dev
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env 填入真实 key
```

需要的 key：
| Key | 用途 | 必需 | 申请地址 |
|-----|------|------|---------|
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | LLM（火山方舟，OpenAI 兼容） | ✅ | https://www.volcengine.com/product/ark |
| `AMAP_API_KEY` | 高德地图（景点/天气） | 推荐 | https://lbs.amap.com |
| `GOOGLE_PLACES_API_KEY` | Google Places | ❌ | https://console.cloud.google.com |
| `OPENWEATHER_API_KEY` | OpenWeather | ❌ | https://openweathermap.org |
| `AMADEUS_CLIENT_ID/SECRET` | 机票酒店 | ❌ | https://developers.amadeus.com |

> 未配置的可选 key 不影响运行，对应工具自动跳过。

### 3. 启动

```bash
uvicorn app.main:app --reload
```

- 前端：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 4. 测试

```bash
pytest
```

## API

| 接口 | 说明 |
|------|------|
| `POST /api/chat` | 核心接口，发送消息，返回回复/行程/追问选项 |
| `GET /api/travel/plans` | 行程列表 |
| `GET /api/travel/plans/{id}` | 行程详情 |
| `DELETE /api/travel/plans/{id}` | 删除行程 |
| `GET /health` | 健康检查 |

### 对话示例

```bash
# 闲聊
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'

# 规划行程
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我规划东京5天游，预算5000，喜欢美食"}'

# 修改行程（多轮对话）
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "第三天删掉迪士尼", "conversation_id": "xxx"}'
```

## 项目结构

```
app/
├── main.py                      # FastAPI 入口
├── api/routers/
│   ├── chat.py                  # POST /api/chat
│   ├── travel.py                # 行程 CRUD
│   └── frontend.py              # 聊天 UI
├── agent/
│   ├── graph.py                 # LangGraph 状态图
│   ├── state.py                 # TravelState
│   ├── nodes/                   # 8 个节点
│   ├── prompts.py               # 各节点 prompt
│   └── llm.py                   # AsyncOpenAI
├── tools/                       # 7 个工具 + budget
├── schemas/                     # Pydantic 请求/响应
├── services/                    # 业务逻辑
├── repositories/                # 数据 CRUD
├── models/                      # SQLAlchemy ORM
├── infrastructure/              # DB + Redis + HTTP
└── common/                      # config + exceptions + logging
tests/
```

## 技术栈

| 层 | 选型 |
|----|------|
| Web 框架 | FastAPI |
| Agent 框架 | LangGraph |
| LLM | 火山方舟（OpenAI 兼容接口） |
| 数据源 | 高德地图 · Google Places · OpenWeather · OSRM · Amadeus |
| ORM | SQLAlchemy |
| 数据库 | SQLite（可切 MySQL） |
| 缓存 | 内存 TTL（可切 Redis） |
| 校验 | Pydantic v2 |
| 测试 | pytest + respx |

## 安全说明

- **默认 `AMADEUS_ENV=test`**：下单只返回模拟 PNR，不真实扣款
- **API key 走 `.env`**，已 in `.gitignore`
- **不做用户注册/登录/JWT/RBAC**，保持简洁

## License

Apache-2.0
