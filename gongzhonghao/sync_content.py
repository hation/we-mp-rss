#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能3：批量补抓文章正文（针对 has_content=0 的文章）。

用法:
  python gongzhonghao/sync_content.py                      # 补抓所有缺正文的文章
  python gongzhonghao/sync_content.py --today              # 只补抓今天的
  python gongzhonghao/sync_content.py --mp MP_WXS_xxx      # 只补抓指定公众号的
  python gongzhonghao/sync_content.py --limit 50           # 只处理前50篇
  python gongzhonghao/sync_content.py --force              # 强制重新抓取（含已有正文的）

说明：直接调用项目内的 core.article_content.sync_article_content，走 api 模式（不依赖Playwright）。
"""
import argparse
import time
from datetime import datetime, timedelta

from _common import print_summary


def main():
    ap = argparse.ArgumentParser(description="批量补抓文章正文")
    ap.add_argument("--today", action="store_true", help="只处理今天的文章")
    ap.add_argument("--days", type=int, default=0, help="只处理最近N天的文章")
    ap.add_argument("--mp", default=None, help="只处理指定公众号ID")
    ap.add_argument("--limit", type=int, default=0, help="最多处理N篇，0=不限")
    ap.add_argument("--force", action="store_true", help="强制重新抓取（含已有正文的）")
    ap.add_argument("--interval", type=int, default=3, help="每篇间隔秒数（默认3）")
    args = ap.parse_args()

    # 延迟导入，确保 _common 的 sys.path 设置生效
    from core.db import DB
    from core.models.article import Article
    from core.article_content import sync_article_content

    session = DB.get_session()

    query = session.query(Article).filter(Article.status != 2)  # 排除已删除
    if not args.force:
        query = query.filter(Article.has_content == 0)
    if args.mp:
        query = query.filter(Article.mp_id == args.mp)
    if args.today:
        today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        query = query.filter(Article.publish_time >= today_start)
    elif args.days:
        start = int((datetime.now() - timedelta(days=args.days)).timestamp())
        query = query.filter(Article.publish_time >= start)

    query = query.order_by(Article.publish_time.desc())
    if args.limit:
        query = query.limit(args.limit)

    arts = query.all()
    print(f"待补抓正文: {len(arts)} 篇" + ("（强制重抓）" if args.force else ""))
    print("=" * 60)

    ok, fail = [], []
    for i, a in enumerate(arts, 1):
        title = (a.title or "")[:40]
        print(f"[{i}/{len(arts)}] {title}")
        try:
            success, mode = sync_article_content(session, a, preferred_mode="api", force=args.force)
            if success:
                content_len = len(a.content or "")
                print(f"  OK (mode={mode}, len={content_len})")
                ok.append(title)
            else:
                print(f"  FAIL (mode={mode})")
                fail.append((title, f"mode={mode}"))
        except Exception as e:
            print(f"  异常: {e}")
            fail.append((title, str(e)))
        time.sleep(args.interval)

    session.close()
    print_summary("补抓正文完成", ok, fail)


if __name__ == "__main__":
    main()
