# Codegraph MCP Server v1 实现计划

> **说明**: 本变更为追溯性归档，实现已在 v1 完成。本计划记录实际执行路径。

**Goal:** 将 MySQL 代码知识图谱通过 MCP 暴露给 Claude Code，提供 15 个领域语义查询工具。

**Architecture:** Python FastMCP stdio server → DBUtils 连接池 → PyMySQL 参数化查询 → 14 表 ER 模型。工具层封装关联跳转，sql_query 提供只读兜底。

**Tech Stack:** Python 3, FastMCP, PyMySQL, DBUtils, MySQL 8

---

## Task 1: MCP Server 骨架

- [x] **Step 1:** 创建 codegraph-server.py，注册 FastMCP 实例
- [x] **Step 2:** 实现 get_pool() 与环境变量读取
- [x] **Step 3:** 实现 _schema() 校验与 q() 查询辅助

## Task 2: 导航工具

- [x] **Step 1:** list_schemas — SHOW DATABASES 过滤系统库
- [x] **Step 2:** schema_overview — 遍历 ALL_TABLES 统计 COUNT
- [x] **Step 3:** search — 四表 LIKE 模糊匹配

## Task 3: 流程与状态机工具

- [x] **Step 1:** find_service_entry / get_service_entry 含关联解析
- [x] **Step 2:** get_flow / get_state
- [x] **Step 3:** get_flow_statemachine — defaultdict 聚合 activities/transitions

## Task 4: 逻辑链与 Java 工具

- [x] **Step 1:** resolve_chain — 解析 before_beans FQN 到 java_classes
- [x] **Step 2:** find_bean / find_class / get_class / find_method

## Task 5: 安全与文档

- [x] **Step 1:** sql_query — _FORBIDDEN 正则 + 单语句校验 + 自动 LIMIT
- [x] **Step 2:** 编写 ER.md Mermaid ER 图

## Task 6: 集成验证

- [x] **Step 1:** mcp.run() stdio 启动验证
- [x] **Step 2:** 对真实 schema 冒烟测试导航与搜索工具
