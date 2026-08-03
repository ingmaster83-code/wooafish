# -*- coding: utf-8 -*-
"""_rawdata/list_raw_harbor.json + detail_raw_harbor.json -> _data/fishing_spots.json 에 병합
TourAPI 항구/포구(A01011400)를 새 낚시터 유형 'port'로 추가한다."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST_SRC = ROOT / "_rawdata" / "list_raw_harbor.json"
DETAIL_SRC = ROOT / "_rawdata" / "detail_raw_harbor.json"
DATA_OUT = ROOT / "_data" / "fishing_spots.json"

REGION_ALIAS = {
    "경기도": "경기", "경기": "경기",
    "인천광역시": "인천", "인천": "인천",
    "강원특별자치도": "강원", "강원도": "강원", "강원": "강원",
    "충청북도": "충북", "충북": "충북",
    "충청남도": "충남", "충남": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전북": "전북",
    "전라남도": "전남", "전남": "전남",
    "경상북도": "경북", "경북": "경북",
    "경상남도": "경남", "경남": "경남",
    "대구광역시": "대구", "대구": "대구",
    "울산광역시": "울산", "울산": "울산",
    "부산광역시": "부산", "부산": "부산",
    "광주광역시": "광주", "광주": "광주",
    "세종특별자치시": "세종", "세종시": "세종", "세종": "세종",
    "대전광역시": "대전", "대전": "대전",
    "제주특별자치도": "제주", "제주도": "제주", "제주": "제주",
    "서울특별시": "서울", "서울": "서울",
}

REGION_SLUG = {
    "경기": "gyeonggi", "인천": "incheon", "강원": "gangwon",
    "충북": "chungbuk", "충남": "chungnam",
    "전북": "jeonbuk", "전남": "jeonnam",
    "경북": "gyeongbuk", "경남": "gyeongnam",
    "대구": "daegu", "울산": "ulsan", "부산": "busan",
    "광주": "gwangju", "세종": "sejong", "대전": "daejeon",
    "제주": "jeju", "서울": "seoul",
}

GWANGJU_CITY_HINTS = ("동구", "서구", "남구", "북구", "광산구")


def normalize_region(addr):
    if not addr:
        return None
    first = addr.split()[0]
    if first == "전남광주통합특별시":
        tokens = addr.split()
        city_token = tokens[1] if len(tokens) > 1 else ""
        if any(h in city_token for h in GWANGJU_CITY_HINTS):
            return "광주"
        return "전남"
    return REGION_ALIAS.get(first)


def extract_city(addr):
    tokens = addr.split()
    return tokens[1] if len(tokens) >= 2 else ""


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").strip()
    return text


def main():
    list_items = json.loads(LIST_SRC.read_text(encoding="utf-8"))
    details = json.loads(DETAIL_SRC.read_text(encoding="utf-8"))
    existing = json.loads(DATA_OUT.read_text(encoding="utf-8"))

    region_seq = {}
    new_spots = []
    skipped = 0

    for it in list_items:
        cid = it["contentid"]
        detail = details.get(cid, {})

        name = (it.get("title") or "").strip()
        addr = (detail.get("addr1") or it.get("addr1") or "").strip()
        if not name or not addr:
            skipped += 1
            continue

        region = normalize_region(addr)
        if not region:
            skipped += 1
            continue
        region_slug = REGION_SLUG[region]
        city = extract_city(addr)

        region_seq[region_slug] = region_seq.get(region_slug, 0) + 1
        slug = f"{region_slug}-port-{region_seq[region_slug]:03d}"

        overview = strip_html(detail.get("overview", ""))
        lat = detail.get("mapy") or it.get("mapy") or ""
        lng = detail.get("mapx") or it.get("mapx") or ""
        infocenter = strip_html(detail.get("infocenter") or "") or (detail.get("tel") or "")
        parking = (detail.get("parking") or "").strip()

        new_spots.append({
            "slug": slug,
            "spotName": name,
            "region": region,
            "regionSlug": region_slug,
            "city": city,
            "address": addr,
            "lat": lat,
            "lng": lng,
            "typeSlug": "port",
            "typeLabel": "항구/포구",
            "typeIcon": "⚓",
            "phone": infocenter,
            "waterArea": "",
            "species": [],
            "capacity": "",
            "facilityWater": parking if parking not in ("", "-") else "",
            "fee": "",
            "point": overview,
            "safety": [],
            "convenience": [],
            "nearby": "",
            "manageOrg": "",
            "manageTel": "",
            "updated": "",
            "image": detail.get("firstimage") or it.get("firstimage") or "",
        })

    combined = existing + new_spots
    DATA_OUT.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"기존 {len(existing)}개 + 항구/포구 {len(new_spots)}개({skipped}개 스킵) = 총 {len(combined)}개 -> {DATA_OUT}")

    region_count = {}
    for s in new_spots:
        region_count[s["region"]] = region_count.get(s["region"], 0) + 1
    print("항구/포구 지역별:", region_count)


if __name__ == "__main__":
    main()
