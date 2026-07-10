#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能4：文章内容总结，提取每篇核心要点。

用法:
  python gongzhonghao/summarize.py                      # 总结今天的文章
  python gongzhonghao/summarize.py --days 3             # 总结最近3天的
  python gongzhonghao/summarize.py --mp MP_WXS_xxx      # 只总结指定公众号的
  python gongzhonghao/summarize.py --limit 10           # 最多处理10篇
  python gongzhonghao/summarize.py --output summary.md  # 输出到文件

说明：从数据库读取已抓正文的文章，提取纯文本后按主题分类输出Markdown总结。
本脚本不做AI摘要，仅做结构化提取与归类，便于人工快速浏览。
"""
import argparse
from datetime import datetime, timedelta

from _common import print_summary


def extract_text(html: str, max_len: int = 600) -> str:
    """从HTML提取纯文本摘要，去除标签与导航噪声。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # 去除常见微信页面噪声
    noise = ["微信扫一扫", "知道了", "取消", "允许", "在小说阅读器", "去阅读",
             "在小说阅读器中沉浸阅读", "使用完整服务", "轻点两下取消赞",
             "轻点两下取消在看", "使用小程序"]
    for n in noise:
        text = text.replace(n, "")
    text = " ".join(text.split())  # 压缩空白
    return text[:max_len]


def main():
    ap = argparse.ArgumentParser(description="文章内容总结")
    ap.add_argument("--today", action="store_true", help="只总结今天的（默认）")
    ap.add_argument("--days", type=int, default=0, help="总结最近N天的（--today优先）")
    ap.add_argument("--mp", default=None, help="只总结指定公众号ID")
    ap.add_argument("--limit", type=int, default=0, help="最多处理N篇，0=不限")
    ap.add_argument("--output", default=None, help="输出到Markdown文件（不指定则只打印）")
    args = ap.parse_args()

    from core.db import DB
    from core.models.article import Article
    from core.models.feed import Feed

    session = DB.get_session()

    # 时间范围
    if args.today or (not args.days and not args.mp):
        start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    elif args.days:
        start = int((datetime.now() - timedelta(days=args.days)).timestamp())
    else:
        start = 0

    query = session.query(Article).filter(
        Article.has_content == 1,
        Article.status != 2,
        Article.publish_time >= start,
    )
    if args.mp:
        query = query.filter(Article.mp_id == args.mp)
    query = query.order_by(Article.publish_time.desc())
    if args.limit:
        query = query.limit(args.limit)

    arts = query.all()
    print(f"待总结: {len(arts)} 篇")
    print("=" * 60)

    # 公众号ID→名称映射
    feed_map = {}
    if arts:
        feeds = session.query(Feed).all()
        feed_map = {f.id: f.mp_name for f in feeds}

    # 收集每篇摘要
    summaries = []
    for i, a in enumerate(arts, 1):
        pt = datetime.fromtimestamp(a.publish_time).strftime("%m-%d %H:%M")
        mp_name = feed_map.get(a.mp_id, a.mp_id)
        text = extract_text(a.content, 600)
        summaries.append({
            "time": pt,
            "title": a.title or "(无标题)",
            "mp": mp_name,
            "summary": text,
        })
        print(f"[{i}/{len(arts)}] {pt} | {a.title}")

    session.close()

    # 生成Markdown
    md = generate_markdown(summaries)
    print_summary("总结完成", [s["title"] for s in summaries], [])

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n已输出到: {args.output}")
    else:
        print("\n" + "=" * 60)
        print(md)


def generate_markdown(summaries: list) -> str:
    """生成Markdown格式的总结报告。"""
    if not summaries:
        return "无文章可总结。"

    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 公众号文章总结（{today}）", "", f"共 {len(summaries)} 篇文章。", ""]

    for i, s in enumerate(summaries, 1):
        lines.append(f"## {i}. {s['title']}")
        lines.append(f"- 时间：{s['time']} | 来源：{s['mp']}")
        lines.append(f"- 摘要：{s['summary']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
