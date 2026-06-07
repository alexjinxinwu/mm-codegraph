# Browser UI

## Purpose

在 `codegraph_web/` 提供浏览器端**入口外壳**：持久三区域布局（搜索栏 / 主画布占位 / 状态区），通过 schema 选择器与 kind+value 搜索调用 **GET `/api/v1/resolve`**，把外部标识解析为图根节点 seed。界面完整表达 resolve 三态（`found` / `multiple` / `notFound`）及加载/错误态；本能力只负责落 seed，图渲染与 `/expand` 展开由后续 canvas 能力接手。

| 区域 | 职责 |
|------|------|
| 搜索栏 | schema 选择 + kind（commandId / flowId）+ value 输入 |
| 主画布 | `CanvasPlaceholder` 接收 `{ type, id, title?, subtitle? }` seed |
| 状态区 | 三态 UI、加载、错误重试 |

实现位置：`codegraph_web/src/`（React + Vite + TypeScript）；生产构建由 `codegraph_server/app.py` 挂载 `codegraph_web/dist/`。

## Requirements

### Requirement: 浏览器外壳布局

系统 SHALL 提供持久的外壳布局,划分搜索栏、主画布区域与状态区三个区域。画布区域
SHALL 暴露「接收种子节点」的接口;本能力只负责把种子放入画布,节点的渲染与展开
交互不在本能力范围内。布局 SHALL 在窄屏下保持可用。

#### Scenario: 三区域同时可见

- **WHEN** 外壳加载
- **THEN** 搜索栏、主画布区域、状态区均渲染

#### Scenario: 窄屏可用

- **WHEN** 在窄屏(移动端宽度)下渲染
- **THEN** 三个区域均可访问,无横向溢出

---

### Requirement: schema 选择

系统 SHALL 提供 schema 选择器,取值来自允许列表,并作为后续 /resolve 调用的作用域。
未选定 schema 时 SHALL 禁止提交搜索。

#### Scenario: 未选 schema 阻止提交

- **WHEN** 未选定 schema 时尝试提交搜索
- **THEN** 不发起 /resolve 请求

#### Scenario: schema 参与解析

- **WHEN** 已选 schema=S 并提交搜索
- **THEN** /resolve 请求携带 schema=S

---

### Requirement: 搜索控件

系统 SHALL 提供搜索控件,含 kind 选择器与 value 输入。kind 选项 SHALL 镜像
ENTRY_RESOLVERS 已注册入口(至少 commandId 与 flowId)。提交前 SHALL 校验
kind 与 value 非空,不合法时就地提示且不发请求。合法时 SHALL 以 schema + kind +
value 调用 /resolve。

#### Scenario: 缺失输入阻止提交

- **WHEN** kind 或 value 为空时提交
- **THEN** 就地提示,且不发起 /resolve 请求

#### Scenario: 合法提交发起解析

- **WHEN** schema、kind、value 均合法并提交
- **THEN** 以三者为参数调用 /resolve

---

### Requirement: 解析三态的界面表现

系统 SHALL 把 /resolve 的 found / multiple / notFound 三态分别表达为不同界面。
found 时 SHALL 把根节点作为种子交给画布区域;multiple 时 SHALL 渲染候选选择器
并在用户选定后把该候选作为种子;notFound 时 SHALL 渲染空状态,且不作为错误。

#### Scenario: 唯一命中落根

- **WHEN** /resolve 返回 status=found
- **THEN** roots[0] 作为种子节点交给画布区域

#### Scenario: 多命中消歧

- **WHEN** /resolve 返回 status=multiple
- **THEN** 渲染候选选择器,逐个展示候选的 title 与 subtitle

#### Scenario: 选定候选

- **WHEN** 用户从候选选择器中选定一项
- **THEN** 该候选作为种子节点交给画布区域

#### Scenario: 无命中空状态

- **WHEN** /resolve 返回 status=notFound
- **THEN** 渲染空状态提示
- **AND** 不渲染错误样式

---

### Requirement: 加载与错误态

系统 SHALL 在请求进行中渲染加载态并阻止重复提交,在网络或服务端错误时渲染错误态
并提供重试。错误态 SHALL 与 notFound 的空状态区分开。

#### Scenario: 加载中阻止重复提交

- **WHEN** /resolve 请求进行中,用户再次提交
- **THEN** 不发起第二次请求

#### Scenario: 错误态与重试

- **WHEN** /resolve 因网络或服务端错误失败
- **THEN** 渲染错误态并提供重试入口
- **AND** 不复用 notFound 的空状态表现
