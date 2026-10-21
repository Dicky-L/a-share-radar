# 2026-09-21 至 2026-10-20：最近一个月的历史归档

## 分清两种不能互相替代的数据

1. **真实历史股票行情**：按交易日从 BaoStock 历史日K取未复权收盘价、涨跌幅及成交额，输出到 \`data/snapshots/YYYY-MM-DD.json\`，字段与2026-10-20原始快照保持相同的一级结构：\`schema_version/date/market/sectors/stocks/quality/data_sources\`。
2. **ChatGPT 每日18:00选股推送原文**：只有真实生成过且能读取到完整原文的报告，才能写成 \`reports/YYYY-MM-DD.md\` 并标 \`status: original\`。无法找回原文的只能留空或标记 \`summary\`，不可根据事后行情伪造当时的股票推荐。

## 当前能明确核实的日报历史

- 2026-10-15 至 2026-10-19：有5份报告**摘要**，文件已在 \`reports/\` 中，全部保留 \`status: summary\`，绝不当成原始全文。
- 2026-10-20：市场日快照已核验并存在；但相应18:00 ChatGPT推送**完整原文尚未写入** \`reports/2026-10-20.md\`。
- 2026-09-21 至 2026-10-14：目前仓库未有能核验的逐日18:00选股日报原文。不能把这一个月的行情回填当成一个月的真实“历史推荐”。
- 未来要归档该范围原文，需从确实存在的任务历史执行结果拿到完整正文后导入。

## 数据管线（一次性历史回填，无常驻后端）

- \`scripts/backfill_history_shard.py\`：按10月20日快照的5,224只证券名单均匀分8个分片，4个并行 GitHub Actions 执行器，向 BaoStock 逐股请求区间数据（一次请求返回整月日K）。
- \`scripts/merge_history.py\`：要求8个分片全部齐全；交易日历一致；股票代码合法；同日无重复；价格/成交额有效；当日归档覆盖率不低于85%且记录不低于3,000只；任一校验不通过则不发布新历史数据。
- \`.github/workflows/backfill-month.yml\`：首次推送时带 \`[run-month-backfill]\` 的提交会启动；以后只能手动 \`Run workflow\`，避免每次改代码都反复批量抓数。
- 通过验证后会新增各交易日快照及更新 \`data/index.json\`，已存在的10月20日数据保持不变；随后在同一工作流重新构建归档索引和图表数据、发布 Pages。

## 重要数据限制

- 历史候选股票名单使用 **2026-10-20** 的名录和股票简称回溯，因此存在**幸存者偏差**，可能漏掉2026-09-21以后已退市的个股和更名前的曾用名；这不是严格意义上的当日全上市证券清单。
- 不复权价格（BaoStock \`adjustflag=3\`）适合还原当时市场收盘价，跨分红除息日期计算真实投资收益时不能直接拿价格差当总回报。
- BaoStock \`amount\` 的单位是元，需除以一亿元生成 \`turnover_yi\`。2026-10-20现有快照为另一数据来源（腾讯），不得假定不同来源的成交额口径和名单覆盖完全相同。
- \`market.turnover_yi\` 是成功采集样本的成交额**小计**，不是交易所公示的全部市场成交额。
- \`sectors: []\` 表示行业成交额/估算主力净流历史数据暂不可验证；绝不填0冒充没有资金流动。
- 2026年10月1日国庆休市等非交易日不会生成虚假股票收盘数据。日报若在休市日发布，应按报告发布日期归档正文，正文注明最近交易日。
- 凡采集不到真实历史数据时，保留GitHub Actions错误日志，不会生成貌似完整的行情快照。

## 检查入口

- 工作流：<https://github.com/Dicky-L/a-share-radar/actions/workflows/backfill-month.yml>
- 行情历史索引：<https://github.com/Dicky-L/a-share-radar/blob/main/data/index.json>
- 已归档日报：<https://github.com/Dicky-L/a-share-radar/tree/main/reports>
- 选股优先网站：<https://dicky-l.github.io/a-share-radar/>

市场历史数据支持选股复盘和行情图，但**不能取代真实原版推荐/卖出规则**。这些冻结条件必须忠于当时推送。
