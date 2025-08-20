# -*- coding: utf-8 -*-
"""
discover_api.py

Mục đích: Mở trang am.22.cn/ykj/ bằng Playwright và ghi log các request XHR/fetch
để tìm ra endpoint API nội bộ (URL, method, status, headers cơ bản và trích mẫu body).

Chạy:
  1) Cài đặt:  
     C:\\TenMien\\.venv\\Scripts\\python.exe -m pip install playwright
     C:\\TenMien\\.venv\\Scripts\\python.exe -m playwright install chromium

  2) Chạy script:  
     C:\\TenMien\\.venv\\Scripts\\python.exe C:\\TenMien\\discover_api.py

  3) Tại cửa sổ trình duyệt hiện ra, bạn có thể thử bấm lọc/tìm kiếm/phân trang.
     Script sẽ ghi log các request XHR/fetch (ưu tiên những URL chứa "/ykj/").
"""
from __future__ import annotations

import json
import re
import sys
from typing import Optional

from playwright.sync_api import sync_playwright


def short(s: str, n: int = 400) -> str:
    s = s.replace("\r", " ").replace("\n", " ")
    return s[:n] + ("..." if len(s) > n else "")


def run(url: str = "https://am.22.cn/ykj/") -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        def on_response(response):
            try:
                req = response.request
                rtype = req.resource_type
                if rtype not in ("xhr", "fetch"):
                    return
                url_ = response.url
                # Ưu tiên các URL liên quan đến ykj
                if "/ykj/" not in url_ and "/paimai/" not in url_:
                    return
                status = response.status
                method = req.method
                ctype = response.headers.get("content-type", "")
                body_preview = ""
                if "application/json" in ctype:
                    body = response.text()
                    body_preview = short(body, 800)
                elif "text/html" in ctype or "text/plain" in ctype:
                    body_preview = short(response.text(), 800)

                print("\n=== XHR/FETCH ===")
                print(f"{method} {status} {url_}")
                if req.post_data:
                    pdata = req.post_data
                    print(f"POST DATA: {short(pdata, 300)}")
                if body_preview:
                    print(f"RESPONSE SAMPLE: {body_preview}")
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(url, wait_until="domcontentloaded")

        print("\n[discover_api] Trình duyệt đã mở. Hãy thao tác tìm kiếm/lọc/phân trang trong 30-60s...")
        page.wait_for_timeout(45000)

        print("\n[discover_api] Hoàn tất lắng nghe. Đóng trình duyệt.")
        context.close()
        browser.close()


if __name__ == "__main__":
    u = sys.argv[1] if len(sys.argv) > 1 else "https://am.22.cn/ykj/"
    run(u)
