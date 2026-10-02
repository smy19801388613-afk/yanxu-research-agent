# 模拟基金经理建议的独立复核与执行

2026-10-02；基线 d9a86d1 / v0.3.0，工作分支 improve/buy-side-review。第二轮执行者独立读取原评审、源码，并对华宇软件原研究 `013b9220057f4337` 第 7 版做只读复现。模拟评审角色不代表真实基金经理背书。

## 采纳与边界

| 建议 | 处理 | 结果 |
|---|---|---|
| PM-1 当前报告与历史混在同一阅读文件 | 采纳，P1 | Markdown / HTML 默认输出当前稿；新增 audit-markdown / audit-html 输出全部历史。ZIP 同时含 report.md/html、audit.md/html、原样 run.json。全部旧稿保留。 |
| PM-2 ZIP 引用仍依赖发送者本机 | 采纳，P1 | 已打包文档统一放 documents/id.pdf；本地 API 引用及同一原始 PDF URL 改相对链接，保留 #page。manifest.json 记录原 URL、SHA256、文件大小及外链联网依赖；不下载外链。 |
| PM-3 所有 PDF 被标成年度报告 | 采纳，P2 | 统一标识为“PDF 原文”；文种仍由来源原始标题表达，不额外猜测。 |
| PM-4 目录出现太晚 | 采纳前置与键盘入口，P2 | 目录移到摘要后、全部论点前；每份报告独立锚点，章节可获取键盘焦点，保留既有 960px 阅读区和主题。 |
| 目录吸顶与整体换皮 | 本轮不做 | 前置已消除核心导航顺序问题；不增加窄屏遮挡，也不改变现有阅读布局。 |
| 负基期绿色“未计算” | 采纳 | 有 change 时显示金额变化（亿元）并用中性色；缺失保持“待核实”；计算明细与导出同步表达，绝不强套百分比。 |
| 估值与报告关联状态 | 接入另一执行者接口 | MemoView 展示 report_valuation_status 的 changed / unlinked 提醒；导出调用同一个 report_state 函数，不另写推断算法。 |
| 章节及核实问题继续查证 | 采纳最小范围 | 按钮仅切换到对话并预填待编辑问题，不发送、不改写报告。章节修订 diff 本轮延期。 |

## 独立验证

- `tests/test_report_delivery.py` 新增 4 项：当前/审计隔离、六版历史保留、ZIP 相对 PDF 页码和外链、所有文件哈希、原样 JSON、不修改研究、缺失原件清单、金额变动表达。
- 运行 `tests/test_report_delivery.py tests/test_deep_research_v03.py tests/test_core.py tests/test_documents_history.py`：**68 passed**。测试数据库使用 pytest 临时目录；没有真实模型调用。
- `npm.cmd run build`：TypeScript 与 Vite 构建通过（0.3.1）。
- 使用原第 7 版只读载荷调用新导出函数：Markdown **310,744 → 18,634 字符（减少 94.0%）**；当前稿不含旧版 memo JSON；run.json 仍含旧版 1–6。
- ZIP 当前 report.md 的 `/api/documents/` 引用 **0**，已打包 PDF 相对页码引用 **15**；所有 manifest 文件哈希核对通过。外部联网引用 143 项，覆盖当前及历史记录，不代表均已阅读或已下载。
- 原 run 的 memo、memo_revisions、report_revision、valuation_history、updated_at、events 前后完全相同。没有调用写研究/写对话/发消息接口，没有重启服务，没有 commit。
- CUA 浏览器本轮可达：browser id=2，子代理独立隐藏标签。实际看到金额变化中性色；点击估值目录后标题完整可见；展开来源看到半年度报告标识“PDF 原文”；导出菜单显示当前报告与完整审计区分；继续查证只预填输入框且发送按钮保持待点击。已有草稿在检查后恢复。未调整全局 viewport。

证据：[pm-execution-proof.json](pm-execution-proof.json)、[估值锚点截图](pm-execution-anchor.png)、[导出选项截图](pm-execution-export.png)、[预填输入截图](pm-execution-prefill.png)、[估值关联提醒截图](pm-execution-freshness.png)。

## 待根代理补验与限制

- 后端现有服务未重启，本轮真实 HTTP 导出用于复现旧版，修复后的 API 路由由隔离 TestClient 验证；真实第 7 版修复输出通过同份只读载荷调用新导出函数验证。根代理随后安全重启服务：本执行者已通过 GET 复验五种报告/审计/ZIP 路由均为 200，并在价值副本中实际看到 changed 提醒。最后一处中文假设标签微调由本地测试验证，待最终统一重启。
- 本轮验证包内相对路径、页码片段、文件存在及 SHA256，没有宣称已在第三方 PDF 阅读器实测离线页码跳转；页码支持取决于阅读器。
- 浏览器视觉验证采用现有视口，未完成 1366 / 1920 两个指定视口矩阵或全站 WCAG AA 审计。
- 未自动获取所有外部 PDF；不存在的本地原件会进入 unavailable_document_ids，相关引用标 local_service_required，不伪装可离线读取。
