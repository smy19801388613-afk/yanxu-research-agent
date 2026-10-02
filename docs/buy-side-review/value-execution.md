# 价值研究员 · 第二轮独立复核与执行

执行日期：2026-10-02。依据：本组第一轮 `value-review.md` 与 `value-evidence.json`，再独立检查现有实现。基线 `d9a86d1 / v0.3.0`；本轮与其他执行组共享 `improve/buy-side-review` 工作目录。本文件仅报告本组实际执行和验证。

## 独立复核结论

1. **采纳 P2 报告与情景的关联提示。** `save_memo` 原来只保存正文和修订号，既无生成时估值快照，也无可直接读取的关联状态。旧稿继续保留 81.78 亿元本身不是计算错误，风险是另存 21.05 亿元情景后用户无法识别两者关系。不能把总历史长度或全局最新时间当作报告是否已纳入的证明。
2. **采纳金额核验去重。** CFO 长短别名可匹配同一数字；原有 `type + claim` 去重既消不掉长短别名重复，又会吞掉不同位置的完全相同错误。应按指标和金额在文本中的位置识别同一处。
3. **确认负基期问题属于展示层。** `finance.growth` 已输出 `change` 和不能计算同比率的 `reason`；无需修改财务公式。交 PM 组接 `calculations.change`，空值用中性样式。
4. **P1 只读约束仍有效，跨组交接 execute_growth。** 本组确认第一轮请求与证据的一致性，避免与增长组重复修改 `agent.py`。执行层拦截和对应回归由增长组负责。

## 已实现

- 新增纯函数 `app.report_state.report_valuation_status(run)`，提供 `state/message/basis/report_revision/items`。状态为 `no_report`、`no_valuations`、`current`、`changed`、`unlinked`。优先使用实际 `valuation-*` 引用；有生成快照时按方法回退到冻结输入；没有关联的旧稿只能标记“无法确认”。多方法独立比较；同一结果即使历史 ID 不同，也不触发过期提醒。
- 深度生成和基于材料修订均在模型调用前冻结估值情景，并在保存时写入 `memo.valuation_context`（快照、捕获时间、实际引用 IDs）。生成期间新增情景不会被事后伪装成报告已见输入。归档旧稿连同其旧快照保留；不会自动替换正文。
- 关联状态的语义是“报告尚未纳入最新情景，请对照假设”，不声称原情景计算错误。`current` 也明确快照不代表报告逐项讨论了全部情景。
- `valuation.save_result` 改为与同方法最近一版比较，跨方法操作后重复提交等价参数仍复用已有 ID；基数、参数或输出实质变化保留新版本。
- `finance.audit_text` 以指标和金额 span 合并别名重复，并将问题位置保留在返回值；不同位置的相同错误仍分别返回。
- `ValuationLab` 显示相同关联提醒，并纠正“每次修改都生成新情景”的说明。
- 已向根代理交付 GET run 读模型接口，向 PM 组交付报告/导出接口和负基期返回值。GET、MemoView、导出、App 财务卡片由对应组修改，本组不修改这些文件。

## 验证

运行 `.venv\Scripts\python.exe -m pytest tests/test_report_state.py tests/test_deep_research_v03.py tests/test_core.py tests/test_agent_v02.py -q`：**96 passed，1 个已有 Starlette/httpx 弃用警告，15.75 秒**。

新增 `tests/test_report_state.py` 共 18 项用例；写入均在 pytest 临时 SQLite 目录内，不调用真实 LLM：

- PS 增长 1%、倍数 5 得 81.779917230295 亿元；改为 0%、1.3 得 21.05225592067 亿元，状态变更而正文、修订号、旧稿及两份估值保持正确。
- 同参数数字格式不同（`5` / `5.00`）、不同方法交错提交、旧历史等价 ID 不产生虚假提醒。
- 新方法、改基数、显式引用、无关联旧稿、缺少其他方法关联、空快照后新增情景、生成途中改变参数、显式修订后的归档均覆盖。
- 同一 CFO 金额的重叠别名仅报一次；两处相同 CFO 错误保留两项，与利润错误合计三项。
- 负利润基期差额 3.20 亿元、负 CFO 基期差额 0.86 亿元、零基期、正基期和缺失值均核验：负/零基期无普通同比率，有数据时保留金额差额。

另外仅在内存中读取第一轮 `tmp/value-review-original.json` 并添加 `value-evidence.json` 已记录的新情景：原稿先为 `current / references`，添加后为 `changed`；定位到原稿引用的三个 PS 情景 IDs 和新情景 `2208eadbbf08`，确认备忘录对象原样保留。未写回这些文件或用户数据库。

整合回归发现旧测试要求 `PS → PB → 相同 PS` 再造一个 PS ID，与本轮明确的同方法复用行为冲突。审查后保留新行为：PB 不改变 PS 的参数、基数或计算输出，重复提交不应创建一份无实质变化的情景。仅更新旧测试名与断言为 `test_existing_duplicate_history_is_preserved_and_same_method_saves_reused`，完整比较保存历史为原三份 PS 加 PB，确认原有重复历史不被清理、PB 不被覆盖、复用返回值与原 PS 完全相同。基数或参数变化仍由相邻测试验证生成新版本。定向运行 `tests/test_research_retrieval_v03.py tests/test_report_state.py`：**28 passed，2.10 秒**；未重复全量运行。

## 未采纳与限制

- 不自动重写旧稿、不清除历史情景、不假定所有生成输入均被正文采纳；不扩展至自动三表估值或自动交易/报价。
- 本组未修改真实用户 run/chat/memo，未使用真实 LLM，未重启服务，未提交 Git commit。
- 关联快照从本次新生成/修订开始保存；旧稿只有明确引用时才可追溯，缺关联不做臆测迁移。
- 本组仅验证确定性逻辑和临时数据库。页面视觉及导出最终整合由 PM/根代理统一复核，不冒充本组已完成浏览器端到端验收。
