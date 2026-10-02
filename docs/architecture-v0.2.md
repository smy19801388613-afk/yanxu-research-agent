# v0.2 产品与研发说明

## 这次改变了什么

入口从“创建固定研究流程”变为“围绕一个问题持续对话”。原有财务工作台保留为可检查的研究产物；聊天可以讨论，不必每轮重新取数，也可以真正生成估值和报告版本。

| 用户意图 | Agent 可以选择的动作 | 可以核对的产物 |
|---|---|---|
| 查找公司 | 证券目录搜索、身份确认 | 明确的证券代码、公司名 |
| 建立研究基础 | 拉取年度财务、读取披露文件 | 事实、来源、缺失项、计算记录 |
| 查清一个解释 | 在当前年报检索关键词 | 原文片段、页码；未核验信息仍只是线索 |
| 选择估值方法 | 讨论方法适用性、检查字段与缺口 | 方法说明、必要输入 |
| 共同确定假设 | 生成待确认的方案卡片 | 显式参数、理由、待采用状态 |
| 执行或修改估值 | 确定性计算工具 | 新版本结果、假设、与上一版的数值差异 |
| 改变研究重点 | 校验并修订结构化报告 | 当前新稿、旧稿、改动理由 |

## 实现方式

Agent 使用跨模型 JSON 决策协议。模型返回下一步动作或最终回复，后端执行允许的工具并把结果交回模型。它可以选择不调用工具直接讨论；工具执行结果保存在数据库，前端通过 SSE 显示动作和产物。

不依赖单一厂商的原生函数调用格式，因此可通过 OpenAI 兼容接口或 Anthropic Messages 接口使用多个模型。兼容请求格式不等于所有模型都具有相同的工具选择能力，实际质量需要逐模型验收。

明确的报告修改、估值计算、方案卡片请求有完成检查。模型只回复计划时，程序要求它调用相应工具，不能将计划当成操作完成。失败的工具会返回具体错误或缺失输入，结果不会伪装成成功。

财务和估值结果通过 Decimal 计算；模型不能直接覆写历史财务事实。估值新参数需关联用户输入，或来自用户明确采用的已展示方案。报告修改通过事实 ID 与部分数值、口径规则审核。

SQLite 使用原子更新保存估值和报告版本。对话工作进程独立于网页请求；关闭页面后可回来查看。界面呈现公开动作与实际结果，不呈现模型内部推理过程。

## 数据与估值的当前深度

财务底座仍只有年度收入、归母净利润和经营现金流的两年对比。六种估值方法已可执行，但自动取得和核验的估值基数目前只有 PE 所需利润、PS 所需收入。PB 的归母净资产、DCF 的 FCFF、EV/EBITDA 的 EBITDA、DDM 的股利仍依赖用户补充或确认探索假设。

DCF 是恒定预测增速加永续终值的两段计算结构，不是完整三表预测。资金成本、增长、桥接项和股本不自动填值。模型说明也仍需审阅，不能视为财务专家审定意见。

## 下一阶段建议

1. 扩展三表字段字典与口径核验，明确归母权益、少数股东权益、净债务、租赁和投资资产。
2. 做可追溯 FCFF 桥接：EBIT、税率、折旧摊销、资本支出、经营性营运资本。每个调整项能返回原始报表。
3. 引入经营驱动预测和逐年参数，让用户与 Agent 讨论销量、价格、毛利率、费用率、周转天数，再形成现金流。
4. 加入同行可比口径和历史倍数来源，解决“为什么选这个倍数”，而不是只生成倍数。
5. 建立独立金融评测集，覆盖多个行业、亏损企业、来源冲突、重述、负现金流和终值敏感性。
6. 再做公告跟踪、论点失效条件、版本对比和持续研究；交易执行暂不在当前产品范围。

## 本次核对的接口与方法资料

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)：兼容请求与 OpenAI 的输出长度参数。
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create)：独立的 Messages 请求与文本块读取。
- [阿里云 OpenAI 兼容接口](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)：地址、地域及模型配置。现有通用域名仍可用；工作空间专属地址可在设置中编辑。
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)：本地兼容接口。
- [Tushare 股票列表](https://tushare.pro/document/2?doc_id=25)：证券代码、名称和拼音缩写目录。
- [AKShare 年度财报适配源码](https://github.com/akfamily/akshare/blob/main/akshare/stock_feature/stock_three_report_em.py)：公开财报端点、公司类型及字段映射的实现参考。本产品通过 HTTP 直接读取公开响应，未加入 AKShare 运行依赖。
- [Damodaran 财务定义](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/definitions.html)：FCFF 与经营现金流的口径、再投资项目。
- [Damodaran FCFF](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/fcff.html)、[DDM](https://pages.stern.nyu.edu/adamodar/New_Home_Page/lectures/ddm.html)：企业现金流折现与稳定增长股利模型。
