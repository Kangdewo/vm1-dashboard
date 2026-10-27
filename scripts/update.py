#!/usr/bin/env python3
"""用 Python 标准库获取公开信息，更新供低配置安卓设备读取的 JSON。
没有数据时保留各模块上次成功更新的时间；不伪造新闻和预警。
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "dashboard.json"
ALERTS = ROOT / "data" / "official_alerts.json"
UTC = timezone.utc
NOW = datetime.now(UTC)


def utc_now():
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def download(url, timeout=16):
    req = Request(url, headers={"User-Agent": "VM1-HallwayDashboard/1.0 (+GitHub Pages)", "Accept": "application/json,application/rss+xml,application/xml;q=0.9,*/*;q=0.8"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read(950_000)


def get_json(url):
    return json.loads(download(url))


def log(*items):
    print(*items, file=sys.stderr)


def open_meteo():
    query = {
        "latitude": "30.5728", "longitude": "104.0668",
        "timezone": "Asia/Shanghai", "forecast_days": 16,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "hourly": "temperature_2m,weather_code,precipitation_probability",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max",
    }
    response = get_json("https://api.open-meteo.com/v1/forecast?" + urlencode(query))
    if not (response.get("current") and response.get("daily", {}).get("time")):
        raise ValueError("天气返回无有效数据")
    return response


BLOCKED_WORDS = re.compile("明星|饭圈|选秀|八卦|绯闻|综艺|电视剧|演唱会|偶像|游戏直播|网红|娱乐圈|博彩|彩票|足球比赛|电影票房", re.I)


def read_google_rss(query, *, zh=True):
    region = {"hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"} if zh else {"hl": "en-US", "gl": "US", "ceid": "US:en"}
    url = "https://news.google.com/rss/search?" + urlencode({"q": query + " when:1d", **region})
    root = ET.fromstring(download(url))
    result = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        if not title or BLOCKED_WORDS.search(title):
            continue
        pub = (item.findtext("pubDate") or "").strip()
        try:
            dt = parsedate_to_datetime(pub).astimezone(UTC)
        except Exception:
            continue
        if dt < NOW - timedelta(hours=52) or dt > NOW + timedelta(hours=3):
            continue
        source_tag = item.find("source")
        source = source_tag.text.strip() if source_tag is not None and source_tag.text else "Google 新闻聚合"
        suffix = " - " + source
        if title.endswith(suffix):
            title = title[:-len(suffix)]
        link = (item.findtext("link") or "").strip()
        if link and link.startswith("https://"):
            result.append({"title": title[:115], "url": link, "source": source[:36], "published": dt.isoformat(timespec="minutes")})
    return result


def bbc_fallback(category):
    url = "https://feeds.bbci.co.uk/news/world/rss.xml" if category == "world" else "https://feeds.bbci.co.uk/news/business/rss.xml"
    root = ET.fromstring(download(url))
    result = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        if BLOCKED_WORDS.search(title):
            continue
        try:
            dt = parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(UTC)
        except Exception:
            continue
        if dt < NOW - timedelta(hours=52):
            continue
        result.append({"title": title[:115], "url": (item.findtext("link") or ""), "source": "BBC News (EN)", "published": dt.isoformat(timespec="minutes")})
    return result


def fetch_news():
    queries = [
        ("world", 4, ["全球 时政 国际 政策 外交 大国 地缘政治", "国际 冲突 战争 外交 政治"]),
        ("finance", 3, ["全球财经 美联储 黄金 原油 利率 股市", "全球金融 宏观经济 黄金行情 央行"]),
        ("chengdu", 3, ["成都 政策 民生 交通 建设", "成都 四川 城市 经济 规划"]),
    ]
    groups = {}
    success = 0
    for cat, limit, phrases in queries:
        combined = []
        for phrase in phrases:
            try:
                items = read_google_rss(phrase)
                success += 1
                combined.extend(items)
                if len(combined) >= limit + 2:
                    break
            except Exception as e:
                log("新闻RSS失败", cat, str(e))
        if not combined and cat != "chengdu":
            try:
                combined.extend(bbc_fallback(cat))
                success += 1
            except Exception as e:
                log("BBC后备RSS失败", cat, str(e))
        # 聚合新闻新鲜程度优先，来源和标题去重
        combined.sort(key=lambda x: x["published"], reverse=True)
        seen = set()
        groups[cat] = []
        for x in combined:
            title_key = re.sub(r"\W+", "", x["title"].lower())[:65]
            if not title_key or title_key in seen:
                continue
            seen.add(title_key)
            x["category"] = cat
            groups[cat].append(x)
            if len(groups[cat]) >= limit:
                break
    if success == 0:
        raise RuntimeError("所有新闻来源均失败")
    # 交错陈列，但总数不超过10，保证资讯结构比例
    rows = []
    for c in ("world", "finance", "chengdu"):
        rows += groups[c]

    # 保留各类别配额，最终按发布时间从新到旧排序
    rows.sort(key=lambda x: x["published"], reverse=True)
    return rows[:10]


def fetch_quakes():
    params = {
        "format": "geojson", "starttime": (NOW - timedelta(days=7)).date().isoformat(),
        "minlatitude": 27, "maxlatitude": 34,
        "minlongitude": 99, "maxlongitude": 109,
        "minmagnitude": 2.5, "orderby": "time", "limit": 6,
    }
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urlencode(params)
    obj = get_json(url)
    rows = []
    for f in obj.get("features", [])[:6]:
        props = f.get("properties") or {}
        ms = props.get("time")
        if not isinstance(ms, (int, float)):
            continue
        rows.append({"magnitude": props.get("mag"), "place": props.get("place"),
                     "time": datetime.fromtimestamp(ms / 1000, UTC).isoformat(timespec="minutes"),
                     "url": props.get("url")})
    return rows


def fetch_gold():
    obj = get_json("https://api.gold-api.com/price/XAU")
    price = obj.get("price")
    if not isinstance(price, (int, float)) or price <= 0:
        raise ValueError("黄金价格无效")
    return {"price_usd_oz": price, "symbol": "XAU", "updated_at": obj.get("updatedAt") or utc_now(), "source": "Gold API"}


def manual_alerts():
    """此文件只允许添加已核实的官方公告；空数组表示「未接入」，不是「无预警」。"""
    if not ALERTS.exists():
        return []
    src = json.loads(ALERTS.read_text(encoding="utf-8"))
    if not isinstance(src, list):
        return []
    out = []
    for a in src:
        if not isinstance(a, dict):
            continue
        if not all(a.get(s) for s in ("title", "publisher", "source_url", "expires_at")):
            continue
        if not a["source_url"].startswith("https://"):
            continue
        try:
            expiry = datetime.fromisoformat(a["expires_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if expiry > NOW:
            out.append({key: a.get(key, "") for key in ("title", "level", "publisher", "area", "published_at", "expires_at", "source_url")})
    return out[:5]


def main():
    try:
        result = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        result = {}
    errors = []
    operations = [
        ("weather", "weather_updated_at", open_meteo),
        ("news", "news_updated_at", fetch_news),
        ("earthquakes", "earthquakes_updated_at", fetch_quakes),
        ("gold", "gold_updated_at", fetch_gold),
    ]
    updated = 0
    for key, stamp, fn in operations:
        try:
            value = fn()
            result[key] = value
            result[stamp] = utc_now()
            updated += 1
            log("成功更新", key, len(value) if isinstance(value, list) else "")
        except Exception as e:
            errors.append(key + ": " + str(e))
            log("更新失败，保留上次数据", key, str(e))
            result.setdefault(key, [] if key in ("news", "earthquakes") else None)
            result.setdefault(stamp, None)
    result["official_alerts"] = manual_alerts()
    # 没有新数据时不更新updated_at，避免把陈旧内容误标成「已同步」。
    if updated:
        result["updated_at"] = utc_now()
    result["last_attempt_at"] = utc_now()
    result["errors"] = errors
    OUT.parent.mkdir(exist_ok=True, parents=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUT)
    log("完成", updated, "/", len(operations), "模块")
    if updated == 0:
        # 不让Actions直接失败以便保留原有数据并重新安排下次采集
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
