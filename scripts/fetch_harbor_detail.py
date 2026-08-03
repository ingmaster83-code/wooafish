# -*- coding: utf-8 -*-
"""detailCommon2 + detailIntro2 로 각 항구/포구의 상세정보 수집 (병렬)"""
import json
import os
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"
COMMON_URL = "https://apis.data.go.kr/B551011/KorService2/detailCommon2"
INTRO_URL = "https://apis.data.go.kr/B551011/KorService2/detailIntro2"
SCRIPT_DIR = os.path.dirname(__file__)
RAW_LIST = os.path.join(SCRIPT_DIR, "..", "_rawdata", "list_raw_harbor.json")
OUT = os.path.join(SCRIPT_DIR, "..", "_rawdata", "detail_raw_harbor.json")

INTRO_FIELDS = [
    "infocenter", "opendate", "restdate", "expguide", "expagerange",
    "accomcount", "useseason", "usetime", "parking", "chkbabycarriage",
    "chkpet", "chkcreditcard",
]


def http_get_json(url, params, timeout=15):
    full = url + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(full, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_one(content_id):
    common = {}
    intro = {}
    for attempt in range(3):
        try:
            data = http_get_json(COMMON_URL, {
                "serviceKey": API_KEY, "MobileOS": "ETC", "MobileApp": "wooahouse",
                "contentId": content_id, "_type": "json",
            })
            items = data["response"]["body"].get("items", "")
            if items:
                item = items["item"]
                if isinstance(item, list):
                    item = item[0] if item else {}
                common = {
                    "overview": item.get("overview", ""),
                    "tel": item.get("tel", ""),
                    "firstimage": item.get("firstimage", ""),
                    "addr1": item.get("addr1", ""),
                    "addr2": item.get("addr2", ""),
                    "mapx": item.get("mapx", ""),
                    "mapy": item.get("mapy", ""),
                }
            break
        except Exception:
            time.sleep(1.0)

    for attempt in range(3):
        try:
            data = http_get_json(INTRO_URL, {
                "serviceKey": API_KEY, "MobileOS": "ETC", "MobileApp": "wooahouse",
                "contentId": content_id, "contentTypeId": "12", "_type": "json",
            })
            items = data["response"]["body"].get("items", "")
            if items:
                item = items["item"]
                if isinstance(item, list):
                    item = item[0] if item else {}
                intro = {k: item.get(k, "") for k in INTRO_FIELDS}
            break
        except Exception:
            time.sleep(1.0)

    return content_id, {**common, **intro}


def main():
    with open(RAW_LIST, "r", encoding="utf-8") as f:
        items = json.load(f)

    details = {}
    if os.path.exists(OUT):
        with open(OUT, "r", encoding="utf-8") as f:
            details = json.load(f)

    todo = [it["contentid"] for it in items if it["contentid"] not in details]
    print(f"total={len(items)} already_done={len(details)} todo={len(todo)}")

    done_count = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_one, cid): cid for cid in todo}
        for fut in as_completed(futures):
            cid, info = fut.result()
            details[cid] = info
            done_count += 1
            if done_count % 50 == 0:
                print(f"  progress {done_count}/{len(todo)}")
                with open(OUT, "w", encoding="utf-8") as f:
                    json.dump(details, f, ensure_ascii=False)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False)
    print(f"Saved {len(details)} details -> {OUT}")


if __name__ == "__main__":
    main()
