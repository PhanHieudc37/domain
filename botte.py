import os
import sys
import time
import json
import re
from datetime import datetime
import requests
from urllib.parse import quote

from api import get_table_rows, get_recommended_items, get_domain_details

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8499581087:AAHlVefHV4zAcjlLlVr9NbE5eDxxmhbx9rc")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7159305763")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def send_message(text: str) -> bool:
    api = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    # Dùng POST để không phải tự encode
    try:
        resp = requests.post(api, data={"chat_id": CHAT_ID, "text": text}, timeout=20)
        ok = False
        if 200 <= resp.status_code < 300:
            try:
                ok = bool(resp.json().get("ok", True))
            except Exception:
                ok = True
        print(f"[send] status={resp.status_code} ok={ok} text={(text[:60] + '...') if len(text)>60 else text}")
        return ok
    except Exception:
        print("[send] exception when sending message")
        return False


def _chunked(seq, size):
    buf = []
    for x in seq:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def build_domain_list_text(domains: list[str], title: str = "New domain found:") -> str:
    lines = [title]
    lines.extend(domains)
    return "\n".join(lines)


_DOMAIN_RE = re.compile(r"([a-z0-9-]+(?:\.[a-z0-9-]+)+)", re.I)

def _norm_domain(s: str | None) -> str:
    return (s or "").strip().lower()

def _extract_domain(s: str) -> str | None:
    # Tìm chuỗi có dạng domain ở cuối hoặc trong chuỗi
    m = _DOMAIN_RE.search(s)
    return _norm_domain(m.group(1)) if m else None

def load_state(path: str) -> set:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            raw_list: list[str] = []
            if isinstance(data, list):
                raw_list = data
            elif isinstance(data, dict) and "sent" in data and isinstance(data["sent"], list):
                raw_list = data["sent"]
            # Chuẩn hóa: lưu state theo domain (lowercase)
            out: set[str] = set()
            for x in raw_list:
                if not isinstance(x, str):
                    continue
                d = _extract_domain(x)
                if d:
                    out.add(d)
            return out
    except Exception:
        pass
    return set()


def save_state(path: str, keys: set) -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sorted(list(keys)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def is_today(date_str: str | None) -> bool:
    if not date_str:
        return False
    try:
        # Kỳ vọng yyyy-mm-dd
        d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        return d == datetime.now().date()
    except Exception:
        return False


def monitor(url: str, limit: int, delay: float, interval: float, tld: str, state_path: str, only_today: bool, heartbeat_mins: float | None = None):
    sent = load_state(state_path)  # set các domain đã gửi
    print(f"[monitor] start: url={url} tld={tld} limit={limit} interval={interval}s only_today={only_today}")
    last_new_ts = time.time()
    try:
        while True:
            # 1) Thử lấy dữ liệu bảng trực tiếp
            rows = get_table_rows(url, limit=limit)

            # 2) Nếu không có, fallback qua danh sách đề xuất + nạp chi tiết
            if not rows:
                print("[monitor] bảng rỗng -> dùng fallback đề xuất + chi tiết")
                items = get_recommended_items(url, limit=limit)
                rows = []
                for it in items:
                    d = get_domain_details(it.get("detail_url", ""))
                    if not d.get("domain"):
                        d["domain"] = it.get("domain", "")
                    rows.append(d)

            total = len(rows)
            new_rows = []
            for r in rows:
                domain = _norm_domain(r.get("domain"))
                if not domain.endswith(tld.lower()):
                    continue
                if only_today and not is_today(r.get("registration_date")):
                    continue
                if domain not in sent:
                    new_rows.append(r)

            # Khử trùng lặp trong cùng một lô theo domain
            batch_seen: set[str] = set()
            unique_new_rows: list[dict] = []
            for r in new_rows:
                d = _norm_domain(r.get("domain"))
                if d and d not in batch_seen:
                    batch_seen.add(d)
                    unique_new_rows.append(r)

            # Gửi dạng danh sách gọn: "New domain found:\n<domain>\n..."
            new_domains = [d for d in ( _norm_domain(r.get("domain")) for r in unique_new_rows ) if d]
            new_domains = [d for d in new_domains if d]
            for chunk in _chunked(new_domains, 40):  # an toàn < 4096 ký tự
                text = build_domain_list_text(chunk)
                print(f"[monitor] sending list: {len(chunk)} domains")
                send_message(text)
                time.sleep(delay)
            if new_rows:
                last_new_ts = time.time()
                # Cập nhật state + log
                sent.update(new_domains)
                save_state(state_path, sent)
                try:
                    os.makedirs(DATA_DIR, exist_ok=True)
                    log_path = os.path.join(DATA_DIR, "domains.jsonl")
                    ts = datetime.utcnow().isoformat() + "Z"
                    with open(log_path, "a", encoding="utf-8") as f:
                        for d in new_domains:
                            rec = {"domain": d, "first_seen": ts, "source": url}
                            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                except Exception:
                    pass

            print(f"[monitor] fetched={total} new={len(new_rows)} tracked={len(sent)}")
            # Lưu state mỗi vòng để tránh mất tiến trình nếu thoát đột ngột (đã lưu khi có new)
            if not new_rows:
                save_state(state_path, sent)

            # Heartbeat: nếu không có mục mới trong heartbeat_mins, gửi thông báo bot vẫn chạy
            if heartbeat_mins and heartbeat_mins > 0:
                idle_mins = (time.time() - last_new_ts) / 60.0
                if idle_mins >= heartbeat_mins:
                    send_message(f"Vẫn đang theo dõi {tld}. Chưa có mục mới. idle ~{idle_mins:.1f} phút")
                    last_new_ts = time.time()

            print(f"[monitor] sleep {interval}s ...")
            time.sleep(interval)
    except KeyboardInterrupt:
        # yên lặng khi dừng
        save_state(state_path, sent)


def main():
    # CLI: python botte.py [url] [--limit N] [--delay sec] [--monitor] [--interval sec] [--tld .com] [--state path] [--only-today] [--heartbeat-mins M]
    url = "https://am.22.cn/ykj/"
    limit = 20
    delay = 2.0
    interval = 60.0
    monitor_mode = False
    tld = ".com"
    state_path = os.path.join(os.path.dirname(__file__), "sent_state.json")
    only_today = False
    heartbeat_mins: float | None = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("http"):
            url = a
        elif a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1]); i += 1
        elif a == "--delay" and i + 1 < len(args):
            delay = float(args[i + 1]); i += 1
        elif a == "--interval" and i + 1 < len(args):
            interval = float(args[i + 1]); i += 1
        elif a == "--monitor":
            monitor_mode = True
        elif a == "--tld" and i + 1 < len(args):
            tld = args[i + 1]; i += 1
        elif a == "--state" and i + 1 < len(args):
            state_path = args[i + 1]; i += 1
        elif a == "--only-today":
            only_today = True
        elif a == "--heartbeat-mins" and i + 1 < len(args):
            heartbeat_mins = float(args[i + 1]); i += 1
        i += 1

    if monitor_mode:
        monitor(url, limit, delay, interval, tld, state_path, only_today, heartbeat_mins)
        return

    rows = get_table_rows(url, limit=limit)
    if not rows:
        # Fallback: lấy danh sách đề xuất + nạp chi tiết để có giá/ngày...
        items = get_recommended_items(url, limit=limit)
        if not items:
            print("[run] Không lấy được dữ liệu")
            return
        rows = []
        for it in items:
            d = get_domain_details(it["detail_url"])
            if not d.get("domain"):
                d["domain"] = it["domain"]
            rows.append(d)

    rows = [r for r in rows if (r.get("domain") or "").lower().endswith(tld.lower())]

    # Áp dụng kho dữ liệu: chỉ gửi domain mới so với state
    sent = load_state(state_path)
    domains_all = [ _norm_domain(r.get("domain")) for r in rows if r.get("domain") ]
    # Khử trùng lặp trong lô
    seen_once: set[str] = set()
    domains_unique = []
    for d in domains_all:
        if d and d not in seen_once:
            seen_once.add(d)
            domains_unique.append(d)
    # Lọc các domain chưa gửi trước đó
    new_domains = [d for d in domains_unique if d not in sent]

    print(f"[run] will send list with {len(new_domains)} new domains (total fetched {len(domains_unique)})")
    for chunk in _chunked(new_domains, 40):
        text = build_domain_list_text(chunk)
        send_message(text)
        time.sleep(delay)
    print("[run] done")
    # Cập nhật kho dữ liệu + state
    if new_domains:
        sent.update(new_domains)
        save_state(state_path, sent)
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            log_path = os.path.join(DATA_DIR, "domains.jsonl")
            ts = datetime.utcnow().isoformat() + "Z"
            with open(log_path, "a", encoding="utf-8") as f:
                for d in new_domains:
                    rec = {"domain": d, "first_seen": ts, "source": url}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass


if __name__ == "__main__":
    main()
