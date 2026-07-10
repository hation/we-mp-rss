#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能2：批量触发公众号更新，抓取最新文章。

用法:
  python gongzhonghao/update_mps.py                  # 更新全部公众号（每公众号抓2页）
  python gongzhonghao/update_mps.py --pages 3        # 每个公众号抓3页（约15篇）
  python gongzhonghao/update_mps.py --mp MP_WXS_xxx  # 只更新指定公众号
  python gongzhonghao/update_mps.py --interval 10    # 调整间隔为10秒

注意：接口异步执行，触发成功后后台线程会持续抓取，文章会陆续入库。
"""
import argparse
import time

import requests

from _common import BASE, login, auth_headers, print_summary

DEFAULT_PAGES = 2   # 默认每个公众号抓2页（约10篇）
DEFAULT_INTERVAL = 15  # 公众号间隔（秒），避免触发风控


def list_mps(token: str) -> list:
    all_mps = []
    offset = 0
    while True:
        r = requests.get(
            f"{BASE}/wx/mps?offset={offset}&limit=100",
            headers=auth_headers(token),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()["data"]
        batch = data["list"]
        all_mps.extend(batch)
        # 不足一页说明已取完
        if len(batch) < 100:
            break
        offset += 100
    return all_mps


def update_mp(token: str, mp_id: str, pages: int) -> dict:
    r = requests.get(
        f"{BASE}/wx/mps/update/{mp_id}?start_page=0&end_page={pages}",
        headers=auth_headers(token),
        timeout=60,
    )
    try:
        return r.json()
    except Exception:
        return {"raw": r.text, "status": r.status_code}


def main():
    ap = argparse.ArgumentParser(description="批量触发公众号更新")
    ap.add_argument("--pages", type=int, default=DEFAULT_PAGES, help=f"每个公众号抓取页数（默认{DEFAULT_PAGES}）")
    ap.add_argument("--mp", default=None, help="只更新指定公众号ID（多个用逗号分隔）")
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help=f"公众号间隔秒数（默认{DEFAULT_INTERVAL}）")
    args = ap.parse_args()

    token = login()
    print("登录成功")

    mps = list_mps(token)
    if args.mp:
        targets = {t.strip() for t in args.mp.split(",")}
        mps = [m for m in mps if m["id"] in targets or m["mp_name"] in targets]

    print(f"共 {len(mps)} 个公众号，每个抓 {args.pages} 页，间隔 {args.interval}秒\n")

    ok, fail, skip = [], [], []
    for i, mp in enumerate(mps, 1):
        mp_id, mp_name = mp["id"], mp["mp_name"]
        print(f"[{i}/{len(mps)}] {mp_name} ({mp_id})")
        try:
            resp = update_mp(token, mp_id, args.pages)
        except Exception as e:
            print(f"  异常: {e}")
            fail.append((mp_name, str(e)))
            time.sleep(args.interval)
            continue

        code = resp.get("code")
        if code == 0:
            print(f"  触发成功: {resp.get('message', '')}")
            ok.append(mp_name)
        elif code == 40402:
            print(f"  跳过(更新过于频繁): {resp.get('message', '')}")
            skip.append(mp_name)
        else:
            print(f"  失败: code={code} {resp.get('message', '')}")
            fail.append((mp_name, f"code={code} {resp.get('message', '')}"))

        time.sleep(args.interval)

    print_summary("更新完成", ok, fail, skip)


if __name__ == "__main__":
    main()
