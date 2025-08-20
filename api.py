# -*- coding: utf-8 -*-
import re
import sys
import csv
import json
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Tạo session dùng lại kết nối + tự động retry khi lỗi tạm thời
_SESSION: Optional[requests.Session] = None

def _get_session() -> requests.Session:
	global _SESSION
	if _SESSION is None:
		s = requests.Session()
		retry = Retry(
			total=3,
			connect=3,
			read=3,
			backoff_factor=1.5,
			status_forcelist=(429, 500, 502, 503, 504),
			allowed_methods=("GET", "HEAD"),
		)
		s.mount("https://", HTTPAdapter(max_retries=retry))
		s.mount("http://", HTTPAdapter(max_retries=retry))
		_SESSION = s
	return _SESSION

def _safe_get(url: str, headers: Dict[str, str], timeout: int) -> Optional[requests.Response]:
	try:
		s = _get_session()
		resp = s.get(url, headers=headers, timeout=(10, timeout))  # (connect, read)
		resp.raise_for_status()
		return resp
	except Exception:
		return None

def get_domains(url: str = "https://am.22.cn/ykj/", timeout: int = 20) -> List[str]:
	"""
	Trích xuất danh sách tên miền từ trang một cách linh hoạt.
	- Ưu tiên bắt các link đề xuất có dạng /ykj/chujia_XXXXX.html
	- Fallback: quét bảng nếu có.
	"""
	headers = {
		"User-Agent": (
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
			"(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
		),
		"Accept-Language": "vi,vi-VN;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
		"Connection": "close",
	}

	resp = _safe_get(url, headers, timeout)
	if resp is None:
		return []
	resp.encoding = resp.apparent_encoding or resp.encoding
	soup = BeautifulSoup(resp.text, "html.parser")

	domains: List[str] = []

	# 1) Bắt các anchor trong danh sách đề xuất
	for a in soup.find_all("a", href=True):
		href = a["href"]
		# Các trang chi tiết một giá thường có dạng /ykj/chujia_31435274.html
		if "/ykj/chujia_" in href:
			text = a.get_text(strip=True)
			# tên miền thường chứa dấu chấm và không có khoảng trắng
			if "." in text and " " not in text:
				domains.append(text)

	# 2) Fallback: nếu rỗng, thử quét bảng (nếu có render sẵn)
	if not domains:
		table = soup.find("table")
		if table:
			for row in table.find_all("tr")[1:]:
				first_link = row.find("a")
				if first_link:
					text = first_link.get_text(strip=True)
					if text and "." in text:
						domains.append(text)
				else:
					cols = row.find_all("td")
					if cols:
						cell = cols[0].get_text(strip=True)
						if cell and "." in cell:
							domains.append(cell)

	# Khử trùng lặp, giữ nguyên thứ tự
	seen = set()
	unique_domains = []
	for d in domains:
		d = d.strip()
		# Lọc ra các chuỗi giống tên miền cơ bản
		if re.match(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$", d) and d not in seen:
			seen.add(d)
			unique_domains.append(d)

	return unique_domains


def _extract_first(pattern: str, text: str) -> Optional[str]:
	m = re.search(pattern, text, re.I)
	return m.group(1) if m else None


def get_domain_details(detail_url: str, timeout: int = 20) -> Dict[str, Optional[str]]:
	"""Lấy chi tiết từ trang domain (giá, registrar, ngày đăng ký, thời gian còn lại, ngày hết hạn)."""
	headers = {
		"User-Agent": (
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
			"(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
		)
	}
	r = _safe_get(detail_url, headers, timeout)
	if r is None:
		return {
			"domain": None,
			"price": None,
			"registrar": None,
			"registration_date": None,
			"time_left": None,
			"days_to_expire": None,
			"detail_url": detail_url,
		}
	r.encoding = r.apparent_encoding or r.encoding
	soup = BeautifulSoup(r.text, "html.parser")
	text = soup.get_text(" ", strip=True)

	# Giá: ưu tiên ¥/￥ nnnn
	price = _extract_first(r"(?:¥|￥)\s*([0-9][0-9,]*)", text) or _extract_first(r"价格\D*([0-9][0-9,]*)", text)
	if price:
		price = price.replace(",", "")

	# Registrar: tìm sau từ '注册商'
	registrar = _extract_first(r"注册商[:：\s]*([^\s，,。；;]+)", text)

	# Ngày đăng ký: yyyy-mm-dd
	reg_date = _extract_first(r"(20\d{2}-\d{2}-\d{2})", text)

	# Thời gian còn lại: cụm chứa '剩余时间'
	time_left = _extract_first(r"剩余时间[:：\s]*([^，,。；;]+)", text)

	# Ngày/Ngày đếm ngược đến hết hạn (距到期)
	days_to_expire = _extract_first(r"距到期[:：\s]*(\d+)天", text)

	# Tên miền: cố gắng lấy từ tiêu đề hoặc breadcrumbs
	domain = _extract_first(r"\b([A-Za-z0-9-]+\.[A-Za-z0-9.-]+)\b", text)

	return {
		"domain": domain,
		"price": price,
		"registrar": registrar,
		"registration_date": reg_date,
		"time_left": time_left,
		"days_to_expire": days_to_expire,
		"detail_url": detail_url,
	}


def get_recommended_items(url: str = "https://am.22.cn/ykj/", limit: int = 20) -> List[Dict[str, str]]:
	"""Trả về danh sách {domain, detail_url} từ trang chính/đề xuất."""
	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
	}
	resp = _safe_get(url, headers, 20)
	if resp is None:
		return []
	resp.encoding = resp.apparent_encoding or resp.encoding
	soup = BeautifulSoup(resp.text, "html.parser")

	items: List[Dict[str, str]] = []
	for a in soup.find_all("a", href=True):
		href = a["href"]
		if "/ykj/chujia_" in href:
			domain = a.get_text(strip=True)
			if "." in domain and " " not in domain:
				items.append({
					"domain": domain,
					"detail_url": urljoin(url, href)
				})
				if len(items) >= limit:
					break
	return items


def get_table_rows(url: str = "https://am.22.cn/ykj/", limit: int = 20) -> List[Dict[str, Optional[str]]]:
	"""Parse bảng danh sách chính để lấy đầy đủ cột.
	Trả về list các dict: domain, summary, registrar, price, time_left, registration_date, days_to_expire, detail_url
	"""
	headers = {
		"User-Agent": (
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
			"(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
		),
		"Accept-Language": "vi,vi-VN;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
	}
	resp = _safe_get(url, headers, 20)
	if resp is None:
		return []
	resp.encoding = resp.apparent_encoding or resp.encoding
	soup = BeautifulSoup(resp.text, "html.parser")

	# Tìm table có các header quen thuộc
	candidate_tables = soup.find_all("table")
	table = None
	for t in candidate_tables:
		head_text = t.get_text(" ", strip=True)
		if all(k in head_text for k in ["名称", "当前价格", "剩余时间"]):
			table = t
			break
	if table is None and candidate_tables:
		table = candidate_tables[0]

	rows: List[Dict[str, Optional[str]]] = []
	if not table:
		return rows

	for tr in table.find_all("tr"):
		tds = tr.find_all(["td", "th"])
		if not tds or tds[0].name == "th":
			# bỏ header
			continue
		try:
			# Cột 0: tên miền (có thẻ a)
			a = tds[0].find("a")
			domain = a.get_text(strip=True) if a else tds[0].get_text(strip=True)
			detail_url = urljoin(url, a["href"]) if a and a.has_attr("href") else None

			summary = tds[1].get_text(strip=True) if len(tds) > 1 else None
			registrar = tds[2].get_text(strip=True) if len(tds) > 2 else None
			price = tds[3].get_text(strip=True) if len(tds) > 3 else None
			time_left = tds[4].get_text(strip=True) if len(tds) > 4 else None
			registration_date = tds[5].get_text(strip=True) if len(tds) > 5 else None
			days_to_expire = tds[6].get_text(strip=True) if len(tds) > 6 else None

			if domain and "." in domain:
				rows.append({
					"domain": domain,
					"summary": summary,
					"registrar": registrar,
					"price": price,
					"time_left": time_left,
					"registration_date": registration_date,
					"days_to_expire": days_to_expire,
					"detail_url": detail_url,
				})
				if len(rows) >= limit:
					break
		except Exception:
			continue

	return rows

if __name__ == "__main__":
	try:
		# CLI đơn giản: python api.py [url] [--limit N] [--csv out.csv] [--json out.json] [--details]
		url = "https://am.22.cn/ykj/"
		limit = 20
		out_csv: Optional[str] = None
		out_json: Optional[str] = None
		with_details = False

		args = sys.argv[1:]
		i = 0
		while i < len(args):
			a = args[i]
			if a.startswith("http"):
				url = a
			elif a == "--limit" and i + 1 < len(args):
				limit = int(args[i + 1])
				i += 1
			elif a == "--csv" and i + 1 < len(args):
				out_csv = args[i + 1]
				i += 1
			elif a == "--json" and i + 1 < len(args):
				out_json = args[i + 1]
				i += 1
			elif a == "--details":
				with_details = True
			i += 1

		items = get_recommended_items(url, limit=limit)
		if not items:
			# Fallback: chỉ in danh sách domain nếu có
			domains = get_domains(url)
			if not domains:
				print("Không tìm thấy tên miền nào (trang có thể render bằng JS).")
				sys.exit(0)
			for d in domains:
				print(d)
			sys.exit(0)

		results: List[Dict[str, Optional[str]]] = []
		if with_details:
			for it in items:
				details = get_domain_details(it["detail_url"])
				# Ghi đè domain nếu thiếu ở chi tiết
				if not details.get("domain"):
					details["domain"] = it["domain"]
				results.append(details)
		else:
			results = items  # chỉ domain + link

		# In ra console
		for r in results:
			if with_details:
				print(f"{r.get('domain','')}\t¥{r.get('price','?')}\t{r.get('registration_date','')}\t{r.get('days_to_expire','')}天\t{r.get('detail_url','')}")
			else:
				print(f"{r['domain']}\t{r['detail_url']}")

		# Ghi file nếu cần
		if out_csv:
			fieldnames = list(results[0].keys()) if results else ["domain", "detail_url"]
			with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
				writer = csv.DictWriter(f, fieldnames=fieldnames)
				writer.writeheader()
				for r in results:
					writer.writerow(r)
			print(f"Đã ghi CSV: {out_csv}")

		if out_json:
			with open(out_json, "w", encoding="utf-8") as f:
				json.dump(results, f, ensure_ascii=False, indent=2)
			print(f"Đã ghi JSON: {out_json}")

	except Exception as e:
		print(f"Lỗi khi lấy dữ liệu: {e}")
