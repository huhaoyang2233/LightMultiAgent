# 🧠 LightMultiAgent - 轻量多智能体讨论室

> 一个轻量级的多智能体协作框架，基于 LangChain 构建，专注于解决多智能体对话中的身份漂移问题，通过结构化上下文管理和智能呼叫机制实现稳定的协作对话。

---

## 📋 目录

- [核心特性](#核心特性)
- [架构设计](#架构设计)
  - [三阶段演变：从混乱到有序](#三阶段演变从混乱到有序)
  - [模块化认知循环](#模块化认知循环)
  - [双向呼叫机制](#双向呼叫机制)
  - [结构化上下文对齐](#结构化上下文对齐)
  - [Agent 系统提示词模板](#agent-系统提示词模板)
  - [动态上下文管理](#动态上下文管理)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [核心组件](#核心组件)
- [API 接口](#api-接口)
- [配置说明](#配置说明)
- [设计理念](#设计理念)
- [技术实现](#技术实现)
- [性能优化](#性能优化)
- [许可证](#许可证)

---

## ✨ 核心特性

| 特性 | 说明 | 技术实现 |
|------|------|----------|
| 🎯 **身份稳定性** | 通过结构化上下文避免智能体身份漂移 | `[Sender -> Receiver]` 显式寻址格式 |
| 🔄 **自动角色切换** | 智能体间自动呼叫，无需人工干预 | 工具调用 + 文本解析双重机制 |
| 📝 **显式寻址** | 使用结构化格式确保对话意图清晰 | 正则匹配 + 上下文分析 |
| 🧠 **角色私有视图** | 每个智能体拥有独立的上下文视图 | 选择性记忆 + 私有缓存 |
| ⏱️ **动态轮次管理** | 自适应讨论轮次，适时邀请用户参与 | 随机扩展机制 + 用户介入触发 |
| 🔧 **可扩展架构** | 支持动态添加角色和工具 | JSON 配置 + 模板化提示词 |
| ⚡ **轻量级设计** | 无需复杂依赖，快速启动 | 核心代码 < 500 行 |

---

## ⚡ 轻量级设计

### 设计理念

LightMultiAgent 追求**轻量、简洁、易用**的设计理念：

| 原则 | 说明 |
|------|------|
| **最小依赖** | 仅依赖 LangChain、FastAPI、Uvicorn 等核心库 |
| **快速启动** | 配置简单，一键启动，无需复杂部署 |
| **易扩展** | 通过 JSON 配置文件动态添加角色 |
| **无状态设计** | 核心逻辑无状态，易于水平扩展 |

### 轻量优势

```
┌─────────────────────────────────────────────┐
│           LightMultiAgent 轻量架构          │
├─────────────────────────────────────────────┤
│  依赖数量：仅 5 个核心依赖                   │
│  核心代码：< 500 行                         │
│  启动时间：< 3 秒                           │
│  内存占用：< 100MB                          │
│  响应延迟：< 100ms                          │
└─────────────────────────────────────────────┘
```

### 快速上手

```bash
# 安装依赖（仅需 5 个包）
pip install langchain langchain-openai fastapi uvicorn python-dotenv

# 配置环境变量
echo "LLM_API_KEY=your-key" > .env
echo "LLM_BASE_URL=https://xxx" >> .env

# 启动服务
python main.py
```

---

## 🏗️ 架构设计

### 三阶段演变：从混乱到有序

![三阶段演变](https://github.com/huhaoyang2233/LightMultiAgent/blob/main/images/stages.png?raw=true)

**问题识别**：传统多智能体系统存在三个典型问题：

| 问题类型 | 表现 | 影响 |
|----------|------|------|
| **对话流歧义** | Agent 无法确定消息目标 | 导致无意义的对话循环 |
| **角色混淆** | 身份漂移导致上下文丢失 | 降低对话质量和一致性 |
| **讨论死锁** | 重复讨论，无法推进 | 资源浪费 + 用户体验差 |

**三阶段解决方案**：

**Stage 1: 外部硬编码包装阶段**
- **方法**：通过外部包装注入身份信息
- **输出示例**：`AgentA said: "Yes, I think will rise."`
- **问题**：对话流歧义，无法追踪消息目标

**Stage 2: 显式文本寻址阶段**
- **方法**：在提示词中强制要求显式指定目标角色
- **输出示例**：`@AgentB regarding your point, I think...`
- **问题**：角色混淆/上下文漂移，增加幻觉风险

**Stage 3: 结果导向向量校准阶段** ⭐
- **方法**：使用 `[Role_A -> Role_B] Content` 结构化格式
- **输出示例**：`[AgentC -> AgentA] Regarding your point, the current valuation is high.`
- **优势**：被动校准 + 标准化对齐上下文，实现稳定的角色一致性

---

### 模块化认知循环

![认知循环](https://github.com/huhaoyang2233/LightMultiAgent/blob/main/images/cognitive_cycle.png?raw=true)

框架采用四阶段认知循环（Coordinating → Planning → Executing → Reflecting）：

**1. Coordinating（协调阶段）**
- **任务需求评估**：分析用户请求，确定任务类型
- **上下文与目标评估**：评估当前对话状态，确定讨论目标
- **系统入口点**：决定是否需要工具调用或直接响应

**2. Planning（规划阶段）**
- **分析路径**：规划解决问题的步骤
- **内部思考链（Chain of Thought）**：生成结构化的推理过程

**3. Executing（执行阶段）**
- **工具调用（via MCP）**：调用外部工具获取数据
- **外部数据获取**：获取实时数据或执行特定操作

**4. Reflecting（反思阶段）**
- **执行反馈**：评估执行结果
- **效果分析**：分析工具调用的有效性
- **策略调整**：根据反馈调整后续行动

**核心优势**：
- 轻量级、高效的闭环思考
- 基于工具调用的可控终止机制
- 外部循环框架支持持续对话

---

### 双向呼叫机制

![呼叫机制](https://github.com/huhaoyang2233/LightMultiAgent/blob/main/images/calling_mechanism.png?raw=true)

**主动呼叫（Active Calling）**：

**方式一：工具调用路径**
```python
# 工具调用格式
tool_output = {
    "tool_name": "call_out_tool",
    "args": {
        "current_role_name": "AgentA",
        "target_role_name": "AgentB",
        "content": "message content"
    }
}
```

**方式二：文本解析路径**
- 模式匹配：`[AgentA -> AgentB] message content`
- 备选模式：`[AgentA]message content @AgentB`

**被动回退（Passive Fallback - Admin Agent）**：

当没有明确目标时，管理员 Agent 介入：

| 步骤 | 操作 |
|------|------|
| 1 | 检测到无明确目标或讨论停滞 |
| 2 | 读取最近 2-4 条消息 |
| 3 | 分析所有 Agent 的能力配置 |
| 4 | 智能选择最合适的下一个发言者 |
| 5 | 打破讨论僵局，推进对话 |

**发言人切换机制**：
- 主动呼叫：直接切换到目标角色
- 被动回退：管理员选择下一个角色

---

### 结构化上下文对齐

![上下文对齐](https://github.com/huhaoyang2233/LightMultiAgent/blob/main/images/context_alignment.png?raw=true)

**优化前（身份混乱）**：
- 消息格式：`Yes, I think the stock will rise.`
- 问题：无法确定发言者和目标，导致对话混乱
- 结果："who said? me or you?" 的身份混淆

**优化后（认知清晰）**：
- 消息格式：`[AgentA -> AgentC] Since B confirmed the trap, what is our macro exit strategy?`
- 优势：
  - 每条消息包含显式的发送者和接收者标识
  - 对话流向清晰可追踪
  - Agent 可以准确理解对话意图

**非对称交互逻辑**：
- **点对点对等审查**：特定角色间的直接交流
- **全球共识广播**：向所有角色传达重要信息

---

### Agent 系统提示词模板

![Agent 系统提示词模板](https://github.com/huhaoyang2233/LightMultiAgent/blob/main/images/prompt_template.png?raw=true)

框架采用结构化的系统提示词模板，包含五个核心模块：

| 模块 | 功能 | 实现细节 |
|------|------|----------|
| **1. Identity & Context** | 定义角色身份、专业边界和行为规范 | 指定角色名称、专长领域、行为准则 |
| **2. Peer Agents & Social Topology** | 定义协作环境和其他 Agent 的专业背景 | 列出所有协作 Agent 及其专业领域 |
| **3. Directives & Operational Rules** | 设置操作红线和权限 | 定义工具调用权限、输出格式要求 |
| **4. Explicit Reasoning Chain (CoT) & Tool Loop** | 使用自然语言引导模型进行结构化分析 | 定义思考过程模板、工具调用流程 |
| **5. Output & Stylized Synthesis** | 定义输出格式和风格 | 专业数据丰富 + 自然语言响应 |

**Agent COT 循环**：
```
输入 → 分析与目标评估 → Stock API 调用 → 验证与可视化 → 输出格式优化 → 反馈 → 输入
```

**系统提示词模板示例结构**：
```
你是 {role_name}，{description}

## 身份信息
- 角色名称：{role_name}
- 专业领域：{expertise}
- 行为准则：{behavior_rules}

## 协作 Agent
- AgentA：{description}
- AgentB：{description}

## 操作规则
- 可以直接调用工具，无需用户许可
- 输出必须使用 [Sender -> Receiver] 格式

## 思考过程
1. 分析问题
2. 决定是否需要工具调用
3. 生成结构化响应

## 输出格式
{format_specification}
```

---

### 动态上下文管理

![动态上下文](https://github.com/huhaoyang2233/LightMultiAgent/blob/main/images/dynamic_context.png?raw=true)

**三阶段进化**：

| 阶段 | 名称 | 特点 | 问题 | 解决方案 |
|------|------|------|------|----------|
| **Phase 1** | 朴素累积 | 简单消息列表，逐条追加 | 身份漂移、语义崩溃 | 引入角色标识 |
| **Phase 2** | 角色反转与选择记忆 | 过滤其他 Agent 的思考日志 | 跨领域逻辑污染 | 选择性记忆机制 |
| **Phase 3** | 角色私有缓存 | 个人知识库 + 私有视图 | ✅ 稳定身份、聚焦专业 | 完整解决方案 |

**Phase 3 架构详解**：

```
┌─────────────────────────────────────────────────────────────┐
│                    Personal Knowledge Pool                  │
│  ┌─────────┐  ┌─────────┐  ┌───────────────┐              │
│  │   CoT   │  │  Tool   │  │  Conclusion   │              │
│  └────┬────┘  └────┬────┘  └───────┬───────┘              │
└───────┼────────────┼───────────────┼───────────────────────┘
        │            │               │
        ▼            ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Role Switch Controller                      │
│                    角色切换控制器                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Agent's Private View                      │
│  [AgentB -> AgentA] message1                               │
│  [AgentA -> AgentB] tool_result                            │
│  [AgentA -> AgentC] message2                               │
│  [AgentC -> AgentA] message3                               │
│                          └──→ 只包含与当前角色相关的消息     │
└─────────────────────────────────────────────────────────────┘
```

**关键优化技术**：

| 技术 | 说明 | 效果 |
|------|------|------|
| **动态角色重映射** | 将 Assistant 角色重新映射为 User 角色 | 避免身份混淆 |
| **选择性记忆** | 只保留与当前角色相关的上下文 | 减少上下文膨胀 |
| **私有缓存** | 每个角色独立的知识池 | 保持专业聚焦 |
| **Token 优化** | 过滤无关上下文 | 减少 35%-60% Token 消耗 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 依赖：`langchain`, `langchain-openai`, `fastapi`, `uvicorn`, `python-dotenv`, `pydantic-settings`

### 安装依赖

```bash
cd agents_chat_room
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```env
# LLM 配置
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL_NAME=ep-m-20260227140447-bk2r6

# 服务配置
PORT=8083
DEBUG=true

# 数据库配置（可选）
DB_HOST=localhost
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=password
DB_NAME=chat_room
```

### 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8083` 启动。

---

## 📁 项目结构

```
agents_chat_room/
├── chat_room.py              # 核心聊天室逻辑
├── main.py                   # FastAPI 服务入口
├── config/                   # 配置模块
│   ├── __init__.py
│   ├── prompt_templates.py   # 通用提示词模板
│   ├── roles.json            # 角色定义（JSON 格式）
│   └── settings.py           # 配置管理（Pydantic Settings）
├── chat_agent/               # 智能体模块
│   ├── __init__.py
│   └── state_manager.py      # LangChain 状态管理
├── history/                  # 历史记录管理
│   └── Context_History.py    # 上下文历史管理
├── logs/                     # 日志目录
├── docs/                     # 文档资源
│   ├── stages.png
│   ├── cognitive_cycle.png
│   ├── calling_mechanism.png
│   ├── context_alignment.png
│   ├── prompt_template.png
│   └── dynamic_context.png
├── .env                      # 环境变量
└── requirements.txt          # 依赖清单
```

---

## 🧩 核心组件

### StockChatRoom 核心类

```python
class StockChatRoom:
    def __init__(self):
        # 讨论轮次管理
        self.initial_max_discussion_steps = 5  # 初始最大轮次
        self.max_discussion_steps = 5
        self.has_asked_user = False
        self.discussion_extended = False
        
        # 角色配置加载
        self.roles_config = RoleConfigLoader.load_roles()
        self.all_roles = RoleConfigLoader.get_all_role_names(self.roles_config)
        
        # LangChain LLM 初始化
        self.llm = ChatOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL_NAME,
            temperature=0.7
        )
    
    async def chat_room(self, data: dict):
        """
        主对话循环
        1. 加载历史上下文
        2. 管理员分配发言角色
        3. 角色发言（支持工具调用）
        4. 解析输出，切换角色
        5. 达到最大轮次时邀请用户参与
        """
        # 实现细节见源码
```

### 角色配置 JSON 结构

```json
{
  "roles": {
    "MarketScount": {
      "name": "市场观察员",
      "description": "负责监控市场动态、资金流向、板块轮动",
      "expertise": ["市场监控", "资金分析", "板块轮动"],
      "tools": ["call_out_tool"],
      "behavior_rules": ["保持客观中立", "数据驱动分析"]
    },
    "TrendSeer": {
      "name": "趋势分析专家",
      "description": "擅长趋势判断、技术指标分析、趋势预测",
      "expertise": ["趋势分析", "技术指标", "价格预测"],
      "tools": ["call_out_tool"],
      "behavior_rules": ["基于技术分析", "提供明确观点"]
    },
    "PatternMaster": {
      "name": "形态识别大师",
      "description": "精通技术形态分析、K线模式识别、量价关系",
      "expertise": ["形态分析", "K线识别", "量价关系"],
      "tools": ["call_out_tool"],
      "behavior_rules": ["注重形态信号", "结合成交量分析"]
    },
    "Chat_User": {
      "name": "用户",
      "description": "参与讨论的用户",
      "expertise": ["用户观点", "投资需求"],
      "tools": [],
      "behavior_rules": ["自然语言交流"]
    }
  }
}
```

### 提示词模板系统

```python
class PromptTemplates:
    @staticmethod
    def generate_system_prompt(role_config: dict, all_roles: list) -> str:
        """
        生成结构化的系统提示词
        """
        template = f"""你是 {role_config['name']}，{role_config['description']}

## 身份信息
- 角色名称：{role_config['name']}
- 专业领域：{', '.join(role_config['expertise'])}
- 行为准则：{', '.join(role_config['behavior_rules'])}

## 协作 Agent
{PromptTemplates._format_peer_agents(all_roles, role_config['name'])}

## 操作规则
1. 可以直接调用 call_out_tool 与其他 Agent 沟通
2. 输出必须使用 [Sender -> Receiver] 格式指定目标
3. 保持专业但友好的语气

## 输出格式
当你要发言时，请使用以下格式：
[你的角色 -> 目标角色] 你的发言内容

如果你想邀请用户参与，请使用：
[你的角色 -> Chat_User] 邀请内容
"""
        return template
```

---

## 🔌 API 接口

### POST /chat

发起聊天请求（流式响应）

**请求体**：
```json
{
  "user_config": {
    "user_ID": "user123",
    "chat_ID": "chat_001",
    "user_TOKEN": "your-token"
  },
  "user_message": {
    "target_role": "",
    "query": "分析一下今天的股市行情，各位专家怎么看？"
  },
  "status": "debug"
}
```

**响应**（Server-Sent Events）：
```
data: {"role": "MarketScount", "content": "大家好！今天市场整体表现比较活跃，成交量有所放大..."}
data: {"role": "TrendSeer", "content": "[MarketScount -> TrendSeer] 同意你的观察，从趋势角度来看..."}
data: {"role": "PatternMaster", "content": "[TrendSeer -> PatternMaster] 技术面上确实有一些值得关注的信号..."}
data: {"role": "TrendSeer", "content": "我们已经讨论了5轮，不知道你对我们的分析有什么看法？欢迎分享你的观点！"}
```

### GET /chat_stream

通过 URL 参数发起聊天

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_ID` | string | 是 | 用户 ID |
| `chat_ID` | string | 是 | 聊天 ID |
| `query` | string | 是 | 用户问题 |
| `target_role` | string | 否 | 指定角色 |
| `status` | string | 否 | 状态（debug/production） |

**示例**：
```
GET /chat_stream?user_ID=user123&chat_ID=chat_001&query=分析股市行情&status=debug
```

### GET /health

健康检查接口

**响应**：
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### POST /chat/history

查询聊天历史

**请求体**：
```json
{
  "user_ID": "user123",
  "chat_ID": "chat_001"
}
```

**响应**：
```json
{
  "history": [
    {"role": "user", "content": "分析一下股市行情"},
    {"role": "MarketScount", "content": "今天市场表现活跃..."},
    {"role": "TrendSeer", "content": "[MarketScount -> TrendSeer] 同意你的观察..."}
  ],
  "count": 3
}
```

---

## ⚙️ 配置说明

### 讨论轮次管理机制

```python
# 初始配置
initial_max_discussion_steps = 5  # 初始最大轮次
discussion_extended = False        # 是否已扩展
has_asked_user = False            # 是否已询问用户

# 扩展逻辑（第5轮触发）
if discussion_steps == 5 and not discussion_extended:
    random_extra = random.randint(1, 4)  # 随机扩展 1-4 轮
    max_discussion_steps = 5 + random_extra  # 最大 5-9 轮
    discussion_extended = True

# 用户介入触发
if discussion_steps == max_discussion_steps and not has_asked_user:
    ask_user_content = f"我们已经讨论了{max_discussion_steps}轮，不知道你对我们的分析有什么看法？"
    has_asked_user = True
```

### 工具调用机制

```python
def call_out_tool(current_role_name: str, target_role_name: str, content: str) -> str:
    """
    智能体间呼叫工具
    
    参数：
        current_role_name: 当前发言角色
        target_role_name: 目标角色
        content: 消息内容
    
    返回：工具调用结果
    """
    # 记录角色切换日志
    logging.info(json.dumps({
        "event_type": "role_switch",
        "from_role": current_role_name,
        "to_role": target_role_name,
        "content": content[:50] + "..." if len(content) > 50 else content
    }, ensure_ascii=False))
    
    # 更新目标角色
    self.target_role = target_role_name
    
    return f"已向 {target_role_name} 发送消息"
```

### 输出过滤规则

```python
# 正则模式
pattern1 = r'^\[\s*([\w\-]+)\s*->\s*([\w\-]+)\s*\]'  # [A->B] 格式
pattern2 = r'^\[[^\]]*\]\s*'                            # [B] 格式

# 处理逻辑
if re.match(pattern1, output):
    # 提取目标角色和内容
    match = re.match(pattern1, output)
    target_role = match.group(2)
    clean_content = re.sub(pattern1, '', output).strip()
elif re.match(pattern2, output):
    # 提取内容
    clean_content = re.sub(pattern2, '', output).strip()
else:
    # 保持原样
    clean_content = output
```

---

## 💡 设计理念

### 核心问题：身份漂移

在多智能体对话中，当 Agent 数量增加时，容易出现：

| 问题 | 表现 | 根源 |
|------|------|------|
| **说话者混淆** | 不知道是谁在发言 | 缺乏明确的身份标识 |
| **目标不明确** | 不知道该回应谁 | 缺乏显式的目标指定 |
| **上下文丢失** | 历史消息无法关联 | 缺乏结构化的上下文管理 |

### 解决方案：结构化上下文

通过强制要求 `[Sender -> Receiver]` 格式：

1. **明确来源**：每条消息都有明确的发送者
2. **明确目标**：每条消息都有明确的接收者
3. **清晰流向**：对话流向可追踪
4. **准确意图**：Agent 可以准确理解对话意图

### 设计原则

| 原则 | 说明 | 实现 |
|------|------|------|
| **显式优于隐式** | 显式指定目标角色 | `[A -> B]` 格式 |
| **稳定优于灵活** | 保持角色身份稳定 | 私有视图 + 选择性记忆 |
| **用户参与** | 适时邀请用户加入讨论 | 动态轮次 + 用户介入 |
| **可观测性** | 详细的日志记录 | 结构化日志 + 事件追踪 |
| **可扩展性** | 支持动态添加角色 | JSON 配置 + 模板化 |

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

*Built with ❤️ for Multi-Agent Collaboration*
