# 公众号运维工具集

WeRSS 公众号批量管理脚本集合。所有脚本在项目根目录下执行，使用 `.venv` 虚拟环境。

## 环境变量（可选）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `WERSS_BASE` | `http://localhost:8001/api/v1` | 服务地址 |
| `WERSS_USER` | `admin` | 登录用户名 |
| `WERSS_PASS` | `admin@123` | 登录密码 |
| `WERSS_XLSX` | `gongzhonghao/公众号.xlsx` | 公众号列表Excel |

## 脚本一览

### 1. import_mps.py — 批量导入公众号

从 Excel 第一列读取公众号名称，逐个搜索并添加到系统。

```bash
# 导入全部
.venv/bin/python gongzhonghao/import_mps.py

# 先导入前3个测试
.venv/bin/python gongzhonghao/import_mps.py --limit 3

# 跳过前5个，导入剩余
.venv/bin/python gongzhonghao/import_mps.py --offset 5

# 指定其他Excel文件
.venv/bin/python gongzhonghao/import_mps.py --file /path/to/other.xlsx
```

**Excel格式**：第一个 sheet，第一列为公众号名称，首行表头自动跳过。

### 2. update_mps.py — 批量触发抓取最新文章

触发所有（或指定）公众号的更新接口，抓取最新文章入库。

```bash
# 更新全部公众号（默认每公众号抓2页，约10篇）
.venv/bin/python gongzhonghao/update_mps.py

# 每个公众号抓3页（约15篇）
.venv/bin/python gongzhonghao/update_mps.py --pages 3

# 只更新指定公众号（支持ID或名称，逗号分隔）
.venv/bin/python gongzhonghao/update_mps.py --mp MP_WXS_3920714878
.venv/bin/python gongzhonghao/update_mps.py --mp "专注AI大模型,中国信通院CAICT"

# 调整间隔（默认15秒）
.venv/bin/python gongzhonghao/update_mps.py --interval 10
```

**注意**：接口异步执行，触发成功后后台线程持续抓取，文章会陆续入库。

### 3. sync_content.py — 批量补抓文章正文

对 `has_content=0`（未抓正文）的文章批量补抓，走 api 模式（不依赖 Playwright）。

```bash
# 补抓所有缺正文的文章
.venv/bin/python gongzhonghao/sync_content.py

# 只补抓今天的
.venv/bin/python gongzhonghao/sync_content.py --today

# 补抓最近3天的
.venv/bin/python gongzhonghao/sync_content.py --days 3

# 只补抓指定公众号的
.venv/bin/python gongzhonghao/sync_content.py --mp MP_WXS_3920714878

# 限制最多处理50篇
.venv/bin/python gongzhonghao/sync_content.py --limit 50

# 强制重新抓取（含已有正文的）
.venv/bin/python gongzhonghao/sync_content.py --force --today
```

### 4. summarize.py — 文章内容总结

从数据库读取已抓正文的文章，提取纯文本摘要，输出 Markdown 总结。

```bash
# 总结今天的文章（默认）
.venv/bin/python gongzhonghao/summarize.py

# 总结最近3天的
.venv/bin/python gongzhonghao/summarize.py --days 3

# 只总结指定公众号的
.venv/bin/python gongzhonghao/summarize.py --mp MP_WXS_3920714878

# 输出到文件
.venv/bin/python gongzhonghao/summarize.py --output gongzhonghao/summary.md
```

## 典型工作流

```bash
# 1. 导入公众号（首次）
.venv/bin/python gongzhonghao/import_mps.py --limit 3   # 先测试3个
.venv/bin/python gongzhonghao/import_mps.py              # 全部导入

# 2. 每日抓取最新文章
.venv/bin/python gongzhonghao/update_mps.py

# 3. 补抓缺正文的文章
.venv/bin/python gongzhonghao/sync_content.py --today

# 4. 生成今日总结
.venv/bin/python gongzhonghao/summarize.py --output gongzhonghao/summary_$(date +%Y%m%d).md
```

## 文件结构

```
gongzhonghao/
├── _common.py          # 公共配置（登录、路径、汇总输出）
├── import_mps.py       # 功能1：导入公众号
├── update_mps.py       # 功能2：抓取最新文章
├── sync_content.py     # 功能3：补抓文章正文
├── summarize.py        # 功能4：文章内容总结
├── README.md           # 本文件
└── 公众号.xlsx          # 公众号名称列表
```
