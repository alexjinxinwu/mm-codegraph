## ADDED Requirements

### Requirement: 图画布与种子渲染

系统 SHALL 提供图画布,接收来自外壳的种子节点并渲染为初始图。初始图通常为单个种子
节点、不含边。画布 SHALL 维护节点集与边集,节点以 (type, id) 唯一标识,边以
(源端点, 目标端点, 类型)唯一标识。

#### Scenario: 种子渲染为初始图

- **WHEN** 外壳把一个种子节点交给画布
- **THEN** 画布渲染该节点为初始图
- **AND** 初始图不含边

### Requirement: 节点与边渲染

系统 SHALL 渲染节点的 title 与 subtitle,并使不同 type 的节点在视觉上可区分。系统
SHALL 渲染边,连接其源节点与目标节点。

#### Scenario: 节点展示标题信息

- **WHEN** 渲染一个节点
- **THEN** 展示其 title 与 subtitle

#### Scenario: 类型可区分

- **WHEN** 图中存在不同 type 的节点
- **THEN** 不同 type 的节点在视觉上可区分

### Requirement: 点击展开

系统 SHALL 在节点被点击时以该节点为入参调用 /expand,并把返回的邻居节点与边并入
当前图。展开成功后该节点 SHALL 被标记为已展开。

#### Scenario: 点击触发展开

- **WHEN** 用户点击一个节点
- **THEN** 以该节点为入参调用 /expand

#### Scenario: 邻居并入图

- **WHEN** /expand 返回邻居节点与边
- **THEN** 这些节点与边并入当前图
- **AND** 该被展开节点标记为已展开

### Requirement: 节点与边去重

系统 SHALL 在并入展开结果时去重。已存在于图中的节点(按 (type, id))MUST NOT 被
重复添加;已存在的边(按其端点与类型)MUST NOT 被重复连。

#### Scenario: 节点去重

- **WHEN** 展开结果含一个已在图中的节点
- **THEN** 不新增重复节点

#### Scenario: 边去重

- **WHEN** 展开结果含一条已在图中的边
- **THEN** 不新增重复边

### Requirement: 增量布局稳定性

系统 SHALL 在新元素并入后重新布局,并尽量保持已有节点位置稳定,避免整图大幅跳动。
新节点 SHOULD 放置在被展开节点附近。

#### Scenario: 已有节点位置稳定

- **WHEN** 一次展开把新节点并入图
- **THEN** 已有节点位置基本保持稳定,无整图跳动

### Requirement: 每节点展开态

系统 SHALL 把每次展开的加载态与错误态落在被点击的那个节点上,而非整张画布。展开
进行中 SHALL 阻止对同一节点的重复展开请求,且整图其余部分仍可交互。展开失败
SHALL 在该节点处提供重试,且不影响其它节点。

#### Scenario: 加载态落在被点节点

- **WHEN** 某节点的 /expand 正在进行
- **THEN** 该节点呈现加载态
- **AND** 图中其它节点仍可交互

#### Scenario: 加载中阻止重复展开

- **WHEN** 某节点展开进行中,用户再次点击该节点
- **THEN** 不发起第二次 /expand 请求

#### Scenario: 错误态隔离

- **WHEN** 某节点的 /expand 失败
- **THEN** 该节点呈现错误态并提供重试
- **AND** 其它节点不受影响