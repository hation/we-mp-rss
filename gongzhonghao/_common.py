#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公共配置与工具函数，供 gongzhonghao/ 下各脚本复用。"""
import os
import sys
from pathlib import Path

import requests

# 项目根目录（脚本位于 gongzhonghao/，根目录在上一层）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

# 服务地址与账号（可通过环境变量覆盖）
BASE = os.getenv("WERSS_BASE", "http://localhost:8001/api/v1")
USERNAME = os.getenv("WERSS_USER", "admin")
PASSWORD = os.getenv("WERSS_PASS", "admin@123")

# 默认数据源
XLSX_PATH = os.getenv("WERSS_XLSX", "gongzhonghao/公众号.xlsx")


def login() -> str:
    """登录并返回 access_token。"""
    r = requests.post(
        f"{BASE}/wx/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"]["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def print_summary(title: str, ok: list, fail: list, skip: list | None = None):
    """统一打印汇总结果。"""
    skip = skip or []
    print("\n" + "=" * 60)
    print(f"{title}: 成功 {len(ok)} | 失败 {len(fail)} | 跳过 {len(skip)}")
    if fail:
        print("失败:")
        for n, r in fail:
            print(f"  - {n}: {r}")
    if skip:
        print("跳过:")
        for n, r in skip:
            print(f"  - {n}: {r}")
