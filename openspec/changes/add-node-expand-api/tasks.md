## 1. 端点与输入校验

- [ ] 1.1 新增 POST /expand,请求体 { schema, node: { type, id }, edgeIds? }
- [ ] 1.2 校验 schema 在允许列表内,否则返回校验错误且不查数据库
- [ ] 1.3 校验 node.type 是 graph-core 已知的 14 种 nodeType 之一,否则校验错误
- [ ] 1.4 校验 node.id 非空
- [ ] 1.5 若提供 edgeIds,校验每个 id 都是已注册的 EDGE_RULES 规则 id,且其 from
      等于 node.type,否则校验错误

## 2. 起点水合(hydrate)

- [ ] 2.1 由 NodeSpec(node.type)取得 table 与 id_column(="id")
- [ ] 2.2 按 id 查询该行,SELECT 出后续 forward 边所需的全部源列(并集)+ title +
      subtitle 字段
- [ ] 2.3 id 以绑定参数传入
- [ ] 2.4 行不存在 → 返回 notFound 形态(nodes/edges 为空),HTTP 层不视为错误

## 3. forward 展开

- [ ] 3.1 从 EDGE_RULES 选出所有 from == node.type 的 forward 边(平凡单列、
      复合键、语义、guard 四类皆含)
- [ ] 3.2 提供 edgeIds 则只保留交集,否则展开全部适用 forward 边
- [ ] 3.3 对每条边调用 build_expand_query(rule, hydratedNode, limit)
- [ ] 3.4 经共享查询内核执行参数化查询
- [ ] 3.5 guard 边(bridge.beans)依赖 build_expand_query 内部拆分,水合时确保
      before_beans 源列已取出

## 4. 结果整形、去重与封顶

- [ ] 4.1 每个邻居行用目标 NodeSpec 整形为 node { type, id, title, subtitle }
- [ ] 4.2 每条命中的关系整形为 edge { ruleId, from, to, label }
- [ ] 4.3 nodes 按 (type, id) 去重
- [ ] 4.4 edges 按 (ruleId, fromId, toId) 去重
- [ ] 4.5 每条边的邻居数受硬编码安全上限约束(build_expand_query 的 LIMIT);
      超限仅返回上限内邻居,不报错

## 5. 防护

- [ ] 5.1 起点 id、水合源列值、guard 拆分元素全部以绑定参数传入,无字符串拼接
- [ ] 5.2 输出节点的 id / keys 形态满足下一次 /expand 与前端去重所需,无需转换

## 6. 测试

- [ ] 6.1 单平凡边展开:flows 起点按 flow.states → 返回该 flow 的 states 邻居
- [ ] 6.2 异名平凡边:beans 起点按 bean.java_class → where full_qualified_name =
      水合得到的 bean_class 值,返回对应 java_class
- [ ] 6.3 复合键边:states 起点按 state.activities → where 同时约束 flow_id 与
      state_name(均来自水合行)
- [ ] 6.4 语义边:logics 起点按 logic.activities → where logic = 水合 chain_id 值
- [ ] 6.5 guard 边:bridges 起点按 bridge.beans → where bean_id IN (拆分 before_beans)
- [ ] 6.6 默认展开:不传 edgeIds,返回该 type 全部适用 forward 边邻居
- [ ] 6.7 指定展开:传 edgeIds 仅返回指定边邻居
- [ ] 6.8 去重:多条边指向同一 (type, id) 节点时,nodes 中只出现一次
- [ ] 6.9 封顶:某边邻居超上限时被截断,响应不报错
- [ ] 6.10 起点不存在:返回空 nodes/edges,非错误
- [ ] 6.11 校验:未知 nodeType / 非法 schema / edgeId 与 type 不匹配 → 校验错误,
      不查数据库
- [ ] 6.12 注入:id 与源列值含 SQL 特殊字符时以参数绑定,查询语义不变