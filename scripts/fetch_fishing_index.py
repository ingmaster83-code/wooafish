# -*- coding: utf-8 -*-
"""
fetch_fishing_index.py - 해양수산부 국립해양조사원 바다낚시지수 수집
전국 갯바위/선상 낚시포인트(각 49개소)의 당일 어종별 낚시지수를 모아
_data/fishing_index_lookup.json 생성. 개별 낚시터 페이지에서 좌표 기준
최근접 포인트를 찾아 "오늘의 바다낚시지수" 위젯을 붙이는 데 쓰임.

사용법:
  python scripts/fetch_fishing_index.py
"""
import json
import os
import re
import sys
import time
from pathlib import Path
from collections import defaultdict

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
OUT_FILE = ROOT / "_data" / "fishing_index_lookup.json"
BASE = "https://apis.data.go.kr/1192136/fcstFishingv2/GetFcstFishingApiServicev2"
SERVICE_KEY = os.environ.get("DATA_GO_KR_API_KEY") or "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"

GUBUN_LIST = ["갯바위", "선상"]


def slugify(name):
    s = re.sub(r"[^\w가-힣]+", "-", name).strip("-")
    return s or "point"


def fetch_all(gubun):
    items = []
    page = 1
    while True:
        r = requests.get(
            BASE,
            params={"serviceKey": SERVICE_KEY, "type": "json", "gubun": gubun, "numOfRows": 300, "pageNo": page},
            timeout=30,
        )
        r.raise_for_status()
        d = r.json()
        if d.get("header", {}).get("resultCode") not in ("00", "0"):
            raise SystemExit(f"API 오류({gubun}): {d.get('header')}")
        batch = d.get("body", {}).get("items", {}).get("item") or []
        if not batch:
            break
        items.extend(batch)
        total = d.get("body", {}).get("totalCount", 0)
        if len(items) >= total:
            break
        page += 1
        time.sleep(0.2)
    return items


def main():
    print("=== 바다낚시지수 수집 시작 ===")
    points = {}  # name -> {name, lat, lot, slug, rock: [...], boat: [...]}

    for gubun in GUBUN_LIST:
        key = "rock" if gubun == "갯바위" else "boat"
        raw = fetch_all(gubun)
        print(f"  {gubun}: {len(raw)}건 수신")

        by_point = defaultdict(list)
        for it in raw:
            by_point[it["seafsPstnNm"]].append(it)

        for name, rows in by_point.items():
            p = points.setdefault(name, {
                "name": name,
                "lat": rows[0]["lat"],
                "lot": rows[0]["lot"],
                "slug": slugify(name),
                "rock": [],
                "boat": [],
            })
            # 종별로 대표 1건만(오전/오후 중 지수가 더 좋은 쪽) 남겨서 위젯을 간결하게 유지
            best_by_species = {}
            for row in rows:
                sp = row.get("seafsTgfshNm") or ""
                if not sp or sp == "-":
                    continue
                idx_rank = INDEX_RANK.get(row.get("totalIndex", ""), 0)
                cur = best_by_species.get(sp)
                if cur is None or idx_rank > cur["_rank"]:
                    best_by_species[sp] = {
                        "species": sp,
                        "index": row.get("totalIndex", ""),
                        "date": row.get("predcYmd"),
                        "noon": row.get("predcNoonSeCd"),
                        "waveMin": row.get("minWvhgt"), "waveMax": row.get("maxWvhgt"),
                        "waterTempMin": row.get("minWtem"), "waterTempMax": row.get("maxWtem"),
                        "airTempMin": row.get("minArtmp"), "airTempMax": row.get("maxArtmp"),
                        "tide": row.get("tdlvHrCn"),
                        "_rank": idx_rank,
                    }
            species_list = sorted(best_by_species.values(), key=lambda x: -x["_rank"])
            for s in species_list:
                s.pop("_rank", None)
            p[key] = species_list

    result = [p for p in points.values() if p["rock"] or p["boat"]]
    result.sort(key=lambda p: p["name"])

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n완료: {len(result)}개 낚시포인트 저장 -> {OUT_FILE}")


INDEX_RANK = {"매우좋음": 5, "좋음": 4, "보통": 3, "나쁨": 2, "매우나쁨": 1}


if __name__ == "__main__":
    main()
