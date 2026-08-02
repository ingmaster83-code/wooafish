# -*- coding: utf-8 -*-
"""전국낚시터정보표준데이터(CSV) -> _rawdata/fishing_spots.json 변환"""
import csv
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_rawdata" / "fishing_raw.csv"
OUT = ROOT / "_data" / "fishing_spots.json"

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

# 원본 데이터의 "전남광주통합특별시" 같은 오염된 지역명 보정용 (주소 기반 재판정)
JEONNAM_CITY_HINTS = ("목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군",
                       "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군",
                       "함평군", "영광군", "장성군", "완도군", "진도군", "신안군")
GWANGJU_CITY_HINTS = ("동구", "서구", "남구", "북구", "광산구")

TYPE_MAP = {
    "저수지": {"slug": "reservoir", "label": "저수지", "icon": "🏞️"},
    "바다": {"slug": "sea", "label": "바다", "icon": "🌊"},
    "평지": {"slug": "flatland", "label": "하천/평지", "icon": "🌾"},
    "계곡": {"slug": "valley", "label": "계곡", "icon": "⛰️"},
    "기타": {"slug": "etc", "label": "기타(실내 등)", "icon": "🎣"},
}


def split_tags(raw):
    if not raw or raw.strip() in ("-", ""):
        return []
    parts = re.split(r"[,+]", raw)
    out = []
    for p in parts:
        p = p.strip()
        p = re.sub(r"\s*등\s*$", "", p).strip()
        if p and p not in ("-",) and p not in out:
            out.append(p)
    return out


def normalize_region(addr):
    if not addr:
        return None
    first = addr.split()[0]
    region = REGION_ALIAS.get(first)
    if region == "광주" and first == "전남광주통합특별시":
        # 실제로는 데이터 오염 케이스: 주소 두번째 토큰으로 재판정
        pass
    if first == "전남광주통합특별시":
        tokens = addr.split()
        city_token = tokens[1] if len(tokens) > 1 else ""
        if any(h in city_token for h in GWANGJU_CITY_HINTS):
            return "광주"
        return "전남"
    return region


def extract_city(addr):
    tokens = addr.split()
    if len(tokens) < 2:
        return ""
    return tokens[1]


def main():
    raw = SRC.read_bytes().decode("cp949")
    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)

    region_seq = {}
    spots = []
    skipped = 0

    for r in rows:
        name = (r.get("낚시터명") or "").strip()
        addr = (r.get("소재지도로명주소") or "").strip() or (r.get("소재지지번주소") or "").strip()
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
        slug = f"{region_slug}-{region_seq[region_slug]:04d}"

        raw_type = (r.get("낚시터유형") or "기타").strip()
        type_info = TYPE_MAP.get(raw_type, TYPE_MAP["기타"])

        lat = (r.get("WGS84위도") or "").strip()
        lng = (r.get("WGS84경도") or "").strip()

        fee = (r.get("이용요금") or "").strip()
        if fee in ("-", ""):
            fee = ""

        point = (r.get("주요포인트") or "").strip()
        if point in ("-", "없음"):
            point = ""

        nearby = (r.get("주변관광지") or "").strip()
        if nearby in ("-", "없음"):
            nearby = ""

        phone = (r.get("낚시터전화번호") or "").strip()
        if phone in ("-",):
            phone = ""

        water_area = (r.get("수면적") or "").strip()
        if water_area in ("-", ""):
            water_area = ""

        capacity = (r.get("최대수용인원") or "").strip()
        if capacity in ("-", "0", ""):
            capacity = ""

        facility_water = (r.get("수상시설물유형") or "").strip()
        if facility_water in ("-", "없음", "해당없음"):
            facility_water = ""

        manage_org = (r.get("관리기관명") or "").strip()
        manage_tel = (r.get("관리기관전화번호") or "").strip()
        if manage_tel in ("-",):
            manage_tel = ""

        updated = (r.get("데이터기준일자") or "").strip()

        spots.append({
            "slug": slug,
            "spotName": name,
            "region": region,
            "regionSlug": region_slug,
            "city": city,
            "address": addr,
            "lat": lat,
            "lng": lng,
            "typeSlug": type_info["slug"],
            "typeLabel": type_info["label"],
            "typeIcon": type_info["icon"],
            "phone": phone,
            "waterArea": water_area,
            "species": split_tags(r.get("주요어종")),
            "capacity": capacity,
            "facilityWater": facility_water,
            "fee": fee,
            "point": point,
            "safety": split_tags(r.get("안전시설현황")),
            "convenience": split_tags(r.get("편익시설현황")),
            "nearby": nearby,
            "manageOrg": manage_org,
            "manageTel": manage_tel,
            "updated": updated,
        })

    OUT.write_text(json.dumps(spots, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"총 {len(rows)}행 중 {len(spots)}개 낚시터 저장, {skipped}개 스킵 -> {OUT}")

    region_count = {}
    type_count = {}
    for s in spots:
        region_count[s["region"]] = region_count.get(s["region"], 0) + 1
        type_count[s["typeLabel"]] = type_count.get(s["typeLabel"], 0) + 1
    print("지역별:", region_count)
    print("유형별:", type_count)


if __name__ == "__main__":
    main()
