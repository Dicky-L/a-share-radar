# A股启动与卖出雷达 · MVP

[在线地址（须先启用 GitHub Pages）](https://dicky-l.github.io/a-share-radar/)

## 已发布到代码仓库
- `index.html`：六个可交互模块。无需构建，可直接由 Pages 托管。
- `collect.py`：使用 AKShare 获取沪深A股当日快照，仅盘后采集；交易日历和资金日期不符即拒绝更新；原子发布可改进。
- `data/index.json`：归档索引。初始为空，无模拟市场数据。
- `.github/workflows/collect.yml`：工作日18:15（北京时间）计划采集，成功才提交。
- `.github/workflows/pages.yml`：部署仓库根目录到 Pages。

## 你需要执行
1. GitHub 仓库 → Settings → Pages → Source 选 **GitHub Actions**。
2. Actions → `Deploy radar to GitHub Pages` → **Run workflow**，检查是否成功部署。
3. Actions → `Collect verified AKShare post-close data` → **Run workflow**；如果失败，查看日志。免费行情接口可能被 GitHub 美国机房限流。
4. 回到 Pages 点击“刷新已发布数据”。

## 数据范围与明确限制
- 目前仅实现 **盘后快照**，不是实时交易行情。
- 沪深A股成交额统计包含科创板股票但不含 ETF / 北交所；股票搜索和持仓代码输入排除科创板，范围不同需分别标识。
- 行业成交额/主力买卖明细没有完成同源全量采集，因此行业图显示缺数据，不编造。
- 成功的第一个交易日只会有一个快照；双日对照至少需要连续两个交易日的成功采集。
- A/B/C 自动选股、新闻催化、冻结候选及D+3历史回测尚未实现；当前观察池是手工管理。
- 持仓和观察列表保存在浏览器 localStorage，不是跨设备同步；清除浏览器数据会丢失。
- 未经在线验证的 AKShare 接口可能失败；本项目没有在 GitHub Actions 中成功采集真实行情的证明。
- 未集成实际证券交易、不自动下单。

## 本地运行
```bash
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
pip install -r requirements.txt
python collect.py
```

请只把这些功能看作首个可交互原型，不要把空快照当作股市真实的零值。
