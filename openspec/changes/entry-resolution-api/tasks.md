## 1. 入口解析注册表

- [ ] 1.1 定义 EntryResolver 结构:kind、目标 nodeType、value→查询的映射(目标表、
      匹配列、整形所需的 title/subtitle 列)
- [ ] 1.2 注册 commandId resolver:目标 nodeType = service_entries,按 command_id
      列精确匹配
- [ ] 1.3 注册 flowId resolver:目标 nodeType = flows,按 flow_id 列精确匹配
- [ ] 1.4 校验每个 resolver 的 nodeType 都有对应 NodeSpec,否则加载报错

## 2. 端点与输入校验

- [ ] 2.1 新增 GET /resolve?schema=&kind=&value=
- [ ] 2.2 校验 schema 在允许列表内,否则校验错误且不查数据库
- [ ] 2.3 校验 kind 是已注册的 resolver,否则校验错误
- [ ] 2.4 校验 value 非空,否则校验错误

## 3. 解析执行

- [ ] 3.1 按 kind 选出 resolver
- [ ] 3.2 用 resolver 生成参数化查询,value 绑定参数传入
- [ ] 3.3 经共享查询内核执行
- [ ] 3.4 每行用目标 NodeSpec 整形为 { type, id, title, subtitle }

## 4. 三态判定与整形

- [ ] 4.1 0 行 → status=notFound,roots 与 candidates 均空
- [ ] 4.2 1 行 → status=found,roots 含该节点,candidates 空
- [ ] 4.3 多行 → status=multiple,candidates 列出全部候选,roots 空
- [ ] 4.4 节点形态(type/id/title/subtitle)与 /expand 输出一致,可直接续展开

## 5. 防护

- [ ] 5.1 value 全部以绑定参数传入,无字符串拼接
- [ ] 5.2 notFound 不视为 HTTP 错误,返回正常响应体

## 6. 测试

- [ ] 6.1 commandId 唯一命中 → found,roots 为一个 service_entries 节点
- [ ] 6.2 flowId 唯一命中 → found,roots 为一个 flows 节点
- [ ] 6.3 命中行节点结构可不加转换直接作为 /expand 的 node 输入
- [ ] 6.4 value 无命中 → notFound,roots/candidates 空,非错误
- [ ] 6.5 同一 value 命中多行 → multiple,candidates 含全部候选
- [ ] 6.6 校验:未知 kind → 校验错误,不查数据库
- [ ] 6.7 校验:非法 schema → 校验错误,不查数据库
- [ ] 6.8 校验:value 缺失 → 校验错误,不查数据库
- [ ] 6.9 注入:value 含 SQL 特殊字符时以参数绑定,查询语义不变