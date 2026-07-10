"""每日定时总结今日公众号文章并推送到飞书等通知渠道。

cron: 每天 18:00 执行。可在 config.yaml 通过 `server.daily_summary_enabled` 开关，
通过 `server.daily_summary_cron` 自定义时间。
"""
from datetime import datetime, timedelta

from core.config import cfg
from core.log import logger
from core.print import print_info, print_success, print_error


def _extract_text(html: str, max_len: int = 500) -> str:
    """从 HTML 提取纯文本摘要，去除标签与导航噪声。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    noise = ["微信扫一扫", "知道了", "取消", "允许", "在小说阅读器", "去阅读",
             "在小说阅读器中沉浸阅读", "使用完整服务", "轻点两下取消赞",
             "轻点两下取消在看", "使用小程序"]
    for n in noise:
        text = text.replace(n, "")
    text = " ".join(text.split())
    return text[:max_len]


def _ai_summarize(text: str, title: str = "") -> str:
    """调用大模型生成30-50字核心要点摘要。

    依赖 config.yaml 的 llm 配置段。无 api_key 时返回原文前200字降级。
    """
    api_key = cfg.get("llm.api_key", "")
    if not api_key:
        # 无Key降级：返回原文前200字
        return text[:200]

    base_url = cfg.get("llm.base_url", "https://open.bigmodel.cn/api/paas/v4")
    model = cfg.get("llm.model", "glm-4-flash")

    import httpx

    # 文本过长时截断，避免token超限
    content = text[:2000]
    prompt = (f"请用200字左右概括下面这篇公众号文章的核心要点，"
              f"涵盖主要观点和关键信息，直接输出摘要内容，"
              f"不要加“摘要：”等前缀，不要换行。\n"
              f"标题：{title}\n正文：{content}")

    try:
        url = f"{base_url.rstrip('/')}/chat/completions"
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 400,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        summary = data["choices"][0]["message"]["content"].strip()
        # 清理可能的引号和前缀
        summary = summary.strip("\"'").replace("摘要：", "").strip()
        return summary or text[:200]
    except Exception as e:
        logger.warning(f"AI摘要生成失败，降级为原文: {e}")
        return text[:200]


def build_daily_summary() -> str:
    """构建今日文章总结的 Markdown 文本。无文章时返回空串。"""
    from core.db import DB
    from core.models.article import Article
    from core.models.feed import Feed

    session = DB.get_session()
    try:
        # 今日 0 点起
        start = int(datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0).timestamp())

        arts = session.query(Article).filter(
            Article.has_content == 1,
            Article.status != 2,
            Article.publish_time >= start,
        ).order_by(Article.publish_time.desc()).all()

        if not arts:
            return ""

        # 公众号 ID→名称映射
        feeds = session.query(Feed).all()
        feed_map = {f.id: f.mp_name for f in feeds}

        today = datetime.now().strftime("%Y-%m-%d")
        lines = [f"### 📰 今日公众号内容总结（{today}）",
                 f"共 {len(arts)} 篇文章", ""]

        # 预提取每篇文章的纯文本和元数据
        items = []
        for a in arts:
            pt = datetime.fromtimestamp(a.publish_time).strftime("%H:%M")
            mp_name = feed_map.get(a.mp_id, a.mp_id)
            full_text = _extract_text(a.content, 1500)
            items.append({
                "title": a.title or "(无标题)",
                "pt": pt,
                "mp_name": mp_name,
                "full_text": full_text,
            })

        # 并发生成AI摘要（5并发，避免单篇超时阻塞整体）
        from concurrent.futures import ThreadPoolExecutor
        print_info(f"并发生成 {len(items)} 篇AI摘要...")
        with ThreadPoolExecutor(max_workers=5) as pool:
            summaries = list(pool.map(
                lambda it: _ai_summarize(it["full_text"], it["title"]),
                items,
            ))

        for i, (it, summary) in enumerate(zip(items, summaries), 1):
            lines.append(f"**{i}. {it['title']}**")
            lines.append(f"- ⏰ {it['pt']} ｜ 📢 {it['mp_name']}")
            lines.append(f"- 摘要：{summary}")
            lines.append("")

        return "\n".join(lines)
    finally:
        session.close()


def daily_summary_job():
    """每日定时任务入口：总结今日文章并推送通知。"""
    try:
        print_info("开始执行每日文章总结")
        md = build_daily_summary()
        if not md:
            print_info("今日无已抓正文的文章，跳过推送")
            return

        from jobs.notice import sys_notice
        title = f"每日公众号总结 {datetime.now().strftime('%m-%d')}"
        sys_notice(text=md, title=title, tag="每日总结")
        print_success(f"每日总结已推送: {title}")
    except Exception as e:
        print_error(f"每日总结任务执行失败: {e}")
        logger.exception("daily_summary_job failed")


def start_daily_summary():
    """注册每日总结定时任务到调度器。"""
    from jobs.mps import scheduler

    cron_expr = cfg.get("server.daily_summary_cron", "0 18 * * *")
    enabled = cfg.get("server.daily_summary_enabled", True)

    if not enabled:
        print_info("每日总结任务未启用")
        return

    scheduler.add_cron_job(
        daily_summary_job,
        cron_expr=cron_expr,
        job_id="daily_summary",
        tag="每日总结",
    )
    print_success(f"每日总结任务已启动, cron: {cron_expr}")
