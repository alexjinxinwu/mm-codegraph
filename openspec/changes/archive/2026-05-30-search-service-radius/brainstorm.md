## Design Summary

### 需求概述
提供 Service Impact Search API，通过 `command_id` 或 `flow_id` 查询，追踪其在 ER 关系网络中的所有影响传递，输出受影响文件列表。

### ER 关系网络（13 表）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      service_entries (入口)                                  │
│  command_id / flow_id / chain_id / bean_ref / context_name / xml_path        │
└─────────────────────────────────────────────────────────────────────────────┘
          │           │            │           │              │
          ▼           ▼            ▼           ▼              ▼
    ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌────────────┐
    │  flows    │ │  beans  │ │ interceptors │ │ beans │ │ (xml_path) │
    │  flow_id  │ │ bean_id │ │context_name │ │bean_id│ │  配置文件  │
    └───────────┘ └─────────┘ └──────────┘ └────────┘ └────────────┘
          │
          ▼
    ┌───────────┐
    │  states   │◄── transitions ───────────────────────────────┐
    │  flow_id   │     activity_id / state_name / next_target    │递归
    └───────────┘                                               │
          │                                                     │
          ├──► activities ──[logic:chain_id]──► logics ─────────┤
          │                                                    │
          └──► flow_tasks ──[logic:chain_id]──► logics ─────────┘
                       flow_id

    ┌──────────────────────────────────────────────────────────────┐
    │                         logics                                 │
    │                      chain_id / context_id / xml_path         │
    └──────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
    ┌──────────────┐                        ┌──────────────┐
    │ logic_steps  │                        │   bridges    │
    │  chain_id    │                        │  chain_id    │
    └──────────────┘                        └──────────────┘
          │                                       │
          ▼                                       ▼
    ┌──────────────┐                   ┌──────────────────────────┐
    │ (logic_type) │                   │ before_beans / after_beans│
    └──────────────┘                   │     (Java FQN)            │
                                       └──────────────────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │    beans     │
                                          │ bean_class   │
                                          └──────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │java_classes │
                                          │ java_path   │
                                          └──────────────┘
```

### 完整遍历路径（正向 Forward）

```
service_entry
  │
  ├──[chain_id]──→ logics.chain_id
  │                    │
  │                    ├──[chain_id]──→ logic_steps.chain_id
  │                    │                      └── logic_type
  │                    │
  │                    └──[chain_id]──→ bridges.chain_id
  │                                     ├── before_beans (FQN) ──→ beans.bean_class
  │                                     └── after_beans  (FQN) ──→ beans.bean_class
  │                                                             │
  │                                                             ▼
  │                                                     java_classes.java_path
  │
  ├──[flow_id]──→ flows.flow_id
  │                 │
  │                 ├── entry_point ──→ states.state_name
  │                 │
  │                 └──[flow_id]──→ states
  │                               │
  │                               ├── activities.logic ───→ logics.chain_id (递归)
  │                               │
  │                               └── transitions
  │                                     ├── activity_id ──→ activities.activity_id
  │                                     ├── next_target ──→ states.state_name (递归)
  │                                     └── state_name ──→ states (递归)
  │
  ├──[bean_ref]──→ beans.bean_id ──→ java_classes.java_path
  │
  └──[context_name]──→ interceptors.context_name ──→ interceptors.bean_ref ──→ beans.bean_id ──→ java_classes.java_path
```

### 完整遍历路径（反向 Backward）

```
service_entry (target)
  │
  ├─ 查找哪些 service_entry 的 flow_id 指向当前 flow
  │     service_entry.flow_id = flows.flow_id
  │
  ├─ 查找哪些 service_entry 的 chain_id 指向当前 chain
  │     service_entry.chain_id = logics.chain_id
  │
  ├─ 查找哪些 activities.logic 指向当前 chain
  │     states → activities.activity_id → activities.logic = logics.chain_id
  │
  ├─ 查找哪些 flow_tasks.logic 指向当前 chain
  │     flows.flow_id = flow_tasks.flow_id AND flow_tasks.logic = logics.chain_id
  │
  ├─ 查找哪些 transitions.next_target 指向当前 state
  │     states → transitions WHERE transitions.next_target = states.state_name
  │
  └─ 查找哪些 bridges.before_beans / after_beans 指向当前 bean
        bridges.before_beans = beans.bean_class OR bridges.after_beans = beans.bean_class
```

### 关键字段映射

| 源表 | 关键字段 | 指向目标表 | 指向字段 |
|------|----------|------------|----------|
| service_entries | chain_id | logics | chain_id |
| service_entries | flow_id | flows | flow_id |
| service_entries | bean_ref | beans | bean_id |
| service_entries | context_name | interceptors | context_name |
| flows | flow_id | states | flow_id |
| states | flow_id | transitions | flow_id |
| transitions | activity_id | activities | activity_id |
| transitions | next_target | states | state_name |
| activities | logic | logics | chain_id |
| flow_tasks | logic | logics | chain_id |
| logic_steps | chain_id | bridges | chain_id |
| bridges | before_beans | beans | bean_class |
| bridges | after_beans | beans | bean_class |
| interceptors | bean_ref | beans | bean_id |
| beans | bean_class | java_classes | (FQN match) |

### 影响传递方向

| 方向 | 含义 | 用途 |
|------|------|------|
| **Forward** | 上游 → 下游 | 改A会影响哪些下游服务 |
| **Backward** | 下游 → 上游 | 改B会影响哪些上游服务（当前变更的影响范围） |

### API 设计

```
GET /api/v1/service-impact/search
Query Parameters:
  - commandId: string  (可选，二选一)
  - flowId: string     (可选，二选一)
  - direction: "forward" | "backward" | "both"  (default: "both")
  - maxDepth: int      (最大遍历深度，默认 10)

Response:
  {
    "entryPoint": "CMD_CREATE_ORDER",
    "direction": "both",
    "totalImpacted": 12,
    "files": [
      { "path": "src/.../ValidateBridge.java", "type": "java" },
      { "path": "chains/order-chain.xml", "type": "xml" },
      ...
    ],
    "impactChain": [
      { "from": "service_entry:createOrderApi", "to": "logic:ORDER_CHAIN" },
      { "from": "logic:ORDER_CHAIN", "to": "bridge:BR_ORD_VALIDATE" },
      ...
    ]
  }
```

### 数据模型

```java
// ServiceImpactSearchController.java
@RestController
@RequestMapping("/api/v1/service-impact")
public class ServiceImpactSearchController {
    ServiceImpactSearchService searchService;
}

// ServiceImpactSearchService.java
public class ServiceImpactSearchResult {
    String entryPoint;
    String direction;
    int totalImpacted;
    List<ImpactedFile> files;
    List<ImpactEdge> impactChain;
}

// ServiceImpactSearchRepository.java
// 包含 BFS 图遍历逻辑，沿 ER 关系递归收集
```

---

## Alternatives Considered

### Alternative A: 实时 BFS 图遍历
- **Approach**: 每次查询实时遍历 ER 图，用 BFS/DFS 递归收集所有可达节点
- **Pros**: 数据实时、无冗余存储
- **Cons**: 大图深遍历耗时长、多层 JOIN 查询数据库压力大
- **Why not chosen**: 对于复杂调用链可能超时

### Alternative B: 预计算影响索引 + 缓存
- **Approach**: 数据变更时预计算并存储 `upstream_map` 和 `downstream_map`
- **Pros**: 查询 O(1)，性能最佳
- **Cons**: 索引维护复杂、更新延迟、数据冗余
- **Why not chosen**: 当前数据量级实时遍历可接受，复杂度优先

### Alternative C: 递归 SQL 查询
- **Approach**: 用 MySQL recursive CTE 遍历 ER 关系
- **Pros**: 数据库层面完成、减少应用层数据传输
- **Cons**: 递归 CTE 有深度限制、调试困难、不支持跨库
- **Why not chosen**: MySQL 递归深度限制（默认1000），复杂 ER 关系支持有限

---

## Agreed Approach

**选择: Alternative A - 实时 BFS 图遍历 + 层级遍历**

理由：
1. 当前数据量级适中，实时遍历可接受
2. 代码可读性强，便于调试和扩展
3. 无需维护额外索引，数据一致性有保障
4. 支持灵活的方向和深度控制

实现策略：
- Controller 层做参数校验和响应封装
- Service 层做 BFS 遍历编排，调用多个 Repository
- 各 Repository 负责单一数据源的查询（service_entries / flows / logics / beans）
- 用 `Set<String>` 做去重，`List<ImpactEdge>` 记录完整链路

---

## Key Decisions

1. **双向搜索**：默认返回 `both`，同时展示上游和下游影响
2. **最大深度限制**：`maxDepth=10` 防止无限递归
3. **文件去重**：同一文件只出现一次（按 file_path 判重）
4. **XML 配置也纳入输出**：xml_path 也算作受影响文件
5. **仅追踪状态机正向触发**：transitions 触发下游 flow 时才递归

---

## Open Questions

1. **是否需要过滤"死代码"路径？** 有些 logic_step 可能永不触发
2. **循环依赖处理？** A→B→C→A 这种环路需截断
3. **性能要求？** 单次查询最大响应时间期望是多少？
4. **是否需要缓存？** 高频查询命令（如报表场景）可能需要
