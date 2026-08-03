# -*- coding: utf-8 -*-
"""TourAPI areaBasedList2 로 항구/포구(A01011400) 목록 수집"""
import json
import os
import time
import urllib.request
import urllib.parse

API_KEY = "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"
BASE = "https://apis.data.go.kr/B551011/KorService2/areaBasedList2"
OUT = os.path.join(os.path.dirname(__file__), "..", "_rawdata", "list_raw_harbor.json")


def fetch_page(page_no, num_of_rows=100):
    params = {
        "serviceKey": API_KEY,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "MobileOS": "ETC",
        "MobileApp": "wooahouse",
        "_type": "json",
        "contentTypeId": "12",
        "cat1": "A01",
        "cat2": "A0101",
        "cat3": "A01011400",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            body = data["response"]["body"]
            total = int(body["totalCount"])
            items = body.get("items", "")
            if items == "":
                return [], total
            item_list = items["item"]
            if isinstance(item_list, dict):
                item_list = [item_list]
            return item_list, total
        except Exception as e:
            print(f"  retry p{page_no}: {e}")
            time.sleep(1.5)
    raise RuntimeError(f"failed p{page_no}")


def main():
    all_items = []
    page = 1
    collected = 0
    while True:
        items, total = fetch_page(page)
        all_items.extend(items)
        collected += len(items)
        print(f"page {page}: {len(items)} (total {collected}/{total})")
        if collected >= total or not items:
            break
        page += 1
        time.sleep(0.2)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_items)} records -> {OUT}")


if __name__ == "__main__":
    main()
