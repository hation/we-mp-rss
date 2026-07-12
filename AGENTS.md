# Repository Guidelines

## Project Structure & Module Organization
`main.py` starts the FastAPI server defined in `web.py`. Core backend logic lives in `core/`, HTTP endpoints in `apis/`, page handlers in `views/`, scheduled jobs in `jobs/`, and WeChat/browser drivers in `driver/`. Frontend source is in `web_ui/src/`; built assets are served from `static/`. HTML templates for the legacy views live in `public/templates/`. Docker and deployment files are under `compose/` and `Dockerfiles/`. Keep new docs in `docs/` and utility scripts in `tools/` or `script/`.

## Build, Test, and Development Commands
Install backend dependencies with `pip install -r requirements.txt`, then copy `config.example.yaml` to `config.yaml`. Run the full backend locally with `python main.py -job True -init True`; this starts FastAPI, jobs, and initialization hooks. Frontend development happens in `web_ui/`: `npm install`, `npm run dev`, and `npm run build`. For the MQTT helper in `qtserver/`, use `npm install` and `npm run start`. Docker development should read runtime settings from `/.env`; use `docker compose -f compose/docker-compose.dev.yaml up -d --force-recreate` and avoid hardcoding credentials or proxy settings in compose files.

## Coding Style & Naming Conventions
Follow the existing style before introducing cleanup. Python uses 4-space indentation, snake_case for modules/functions, and grouped feature folders such as `core/notice/` and `apis/`. Vue files in `web_ui/src/views/` use PascalCase filenames like `AccessKeyManagement.vue`; composable utilities and API wrappers use camelCase or lower-case filenames such as `auth.ts` and `messageTask.ts`. There is no enforced formatter config in the repo, so keep imports tidy, avoid broad refactors, and match surrounding conventions.

## Testing Guidelines
Backend test coverage is minimal and mostly lives near the code, for example `core/lax/test_template_parser.py`. Run it from that directory with `cd core/lax && python -m unittest test_template_parser.py`. When touching API, scraping, or scheduler code, also do a local smoke test by starting `python main.py` and exercising the affected UI or endpoint. Frontend changes should at least pass `npm run build`.

## Commit & Pull Request Guidelines
Recent history includes `feat:` commits alongside ad-hoc messages like `1.4.9-Fix`; use Angular-style commits going forward, for example `fix: handle expired WeChat cookies`. Keep the body as `-` prefixed lines without blank lines. Create a fresh working branch before changes; for Codex-assisted work use `codex/YYYY-MM-DD`. PRs should include a short problem statement, the key changes, linked issues when relevant, config or migration notes, and screenshots for UI changes.
This clone should keep `origin` pointed at your fork and `upstream` pointed at `https://github.com/rachelos/we-mp-rss`. Before pushing or opening a PR, fetch upstream and merge the latest `upstream/main` into your working branch if it has advanced.

## Security & Configuration Tips
Do not commit `config.yaml`, `/.env`, tokens, cookies, or data from `data/`. Start from `config.example.yaml` and `/.env.example`, then keep real secrets in local-only config. For deployment environments where WeChat blocks datacenter IPs, prefer the compose `singbox` sidecar and a single `PROXY_URL=` entry in `/.env` instead of modifying host proxy settings or duplicating proxy fields across files. Review `SECURITY.md` before changing auth, webhooks, or access-key flows.

## 公众号运维工具集（gongzhonghao/）
项目内置一组公众号批量管理脚本，位于 `gongzhonghao/`，在项目根目录用 `.venv/bin/python` 执行。当用户提到"导入公众号/抓取文章/补抓正文/总结内容"等需求时，优先调用对应脚本，而非临时手写命令。完整用法见 `gongzhonghao/README.md`。

公共配置在 `gongzhonghao/_common.py`，支持环境变量覆盖：`WERSS_BASE`（服务地址，默认 `http://localhost:8001/api/v1`）、`WERSS_USER`（默认 `admin`）、`WERSS_PASS`（默认 `admin@123`）、`WERSS_XLSX`（公众号列表，默认 `gongzhonghao/公众号.xlsx`）。

### 脚本速查
- **import_mps.py** — 批量导入公众号（从 Excel 第一列读名称）
  - `.venv/bin/python gongzhonghao/import_mps.py`（全部）
  - `.venv/bin/python gongzhonghao/import_mps.py --limit 3`（先测试3个）
  - `.venv/bin/python gongzhonghao/import_mps.py --offset 5`（跳过前5个）
  - `.venv/bin/python gongzhonghao/import_mps.py --file /path/to/other.xlsx`（指定Excel）
- **update_mps.py** — 批量触发抓取最新文章（接口异步，文章陆续入库）
  - `.venv/bin/python gongzhonghao/update_mps.py`（全部，默认每公众号2页约10篇）
  - `.venv/bin/python gongzhonghao/update_mps.py --pages 3`（每公众号3页约15篇）
  - `.venv/bin/python gongzhonghao/update_mps.py --mp MP_WXS_xxx`（指定公众号，支持ID或名称，逗号分隔）
  - `.venv/bin/python gongzhonghao/update_mps.py --interval 10`（调整间隔秒数）
- **sync_content.py** — 批量补抓文章正文（走 api 模式，不依赖 Playwright）
  - `.venv/bin/python gongzhonghao/sync_content.py`（所有缺正文的）
  - `.venv/bin/python gongzhonghao/sync_content.py --today`（只补今天的）
  - `.venv/bin/python gongzhonghao/sync_content.py --days 3`（最近3天）
  - `.venv/bin/python gongzhonghao/sync_content.py --mp MP_WXS_xxx`（指定公众号）
  - `.venv/bin/python gongzhonghao/sync_content.py --limit 50`（最多50篇）
  - `.venv/bin/python gongzhonghao/sync_content.py --force`（强制重抓含已有正文的）
- **summarize.py** — 文章内容总结（提取纯文本摘要，输出 Markdown）
  - `.venv/bin/python gongzhonghao/summarize.py`（今天的，默认）
  - `.venv/bin/python gongzhonghao/summarize.py --days 3`（最近3天）
  - `.venv/bin/python gongzhonghao/summarize.py --mp MP_WXS_xxx`（指定公众号）
  - `.venv/bin/python gongzhonghao/summarize.py --output gongzhonghao/summary.md`（输出到文件）

### 典型工作流
```bash
# 日常：抓最新 → 补正文 → 生成总结
.venv/bin/python gongzhonghao/update_mps.py
.venv/bin/python gongzhonghao/sync_content.py --today
.venv/bin/python gongzhonghao/summarize.py --output gongzhonghao/summary_$(date +%Y%m%d).md
```

### 触发规则
- 用户说"导入公众号" → 跑 `import_mps.py`
- 用户说"抓文章/抓今天文章/更新文章" → 跑 `update_mps.py`，再视情况补 `sync_content.py --today`
- 用户说"补正文/抓正文/抓内容" → 跑 `sync_content.py`（默认 `--today`）
- 用户说"总结/摘要/汇总" → 跑 `summarize.py`
- 用户说"跑一遍完整流程/每日任务" → 按典型工作流顺序执行三步

## 标签总结功能
项目支持对指定标签下某时间段的文章进行 AI 总结，支持并发生成和数据库缓存。

### 功能说明
- 基于标签关联的公众号进行文章筛选
- 支持自定义时间范围
- AI 并发生成摘要（5 线程）
- 数据库缓存，已总结文章不再重复调用
- 支持推送通知到飞书等渠道
- Markdown 格式输出

### 使用方式
**Web UI：**
1. 登录后台 → 标签管理 → 点击「总结」按钮
2. 选择时间范围 → 可选开启「推送通知」→ 点击生成

**API 调用：**
```bash
POST /api/v1/wx/tags/{tag_id}/summary
?start_time=1234567890    // 开始时间戳（秒）
&end_time=1234567890      // 结束时间戳（秒）
&push_notice=false         // 是否推送通知
```

### 触发规则
- 用户说"标签总结/按标签总结/总结标签内容" → 询问用户标签名称和时间范围，调用 API 生成总结
- 用户说"科技标签最近7天总结/xxx标签本周总结" → 解析标签名和时间范围，直接调用 API
- 用户说"把这个标签的文章总结一下并推送到飞书" → 开启 push_notice=true
