"""주간 뉴스 클리핑 수집기 (네이버 검색 API + 지방지 RSS).

- 12권역 단위로 수집 → 권역설정 시트 기반 발송용 후보 시트 누적
- 권역 ↔ 12지파 매핑은 handlers/news_clipping_handler 에서 처리
- 호출 진입점: collect_all_regions() / save_candidates_to_sheet()
"""

import asyncio
import html
import os
import re
import time
from datetime import datetime
from typing import Any

import pytz
import requests

import config
from services.news_categorizer import categorize

try:
    import feedparser  # 지방지 RSS
except ImportError:
    feedparser = None  # 모듈 없으면 RSS 비활성

KST = pytz.timezone("Asia/Seoul")
NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"
USER_AGENT = "GAbongBot/1.0 (+https://github.com/anthropics/claude-code)"

CANDIDATE_SHEET = "주간뉴스후보"
CANDIDATE_HEADERS = [
    "발송", "권역", "지파", "지역", "카테고리",
    "제목", "요약", "링크", "출처", "수집일시",
]
MAX_PER_REGION = 30


REGION_QUERY_MAP: dict[str, list[str]] = {
    "서울경기남부": [
        "서울 강남", "서울 서초", "서울 송파", "서울 강동",
        "경기 성남", "경기 수원", "경기 용인", "경기 화성",
        "경기 안양", "경기 과천", "경기 안산", "경기 평택", "경기 오산",
    ],
    "서울경기북부": [
        "서울 강북", "서울 도봉", "서울 노원", "서울 성북",
        "경기 의정부", "경기 양주", "경기 동두천", "경기 포천",
        "경기 가평", "경기 연천",
    ],
    "서울경기동부": [
        "서울 광진", "서울 성동", "서울 동대문", "서울 중랑",
        "경기 남양주", "경기 구리", "경기 하남", "경기 광주",
        "경기 이천", "경기 여주", "경기 양평",
    ],
    "서울경기서부": [
        "서울 마포", "서울 서대문", "서울 은평", "서울 영등포",
        "서울 강서", "서울 양천", "서울 구로", "서울 금천",
        "경기 부천", "경기 광명", "경기 시흥", "경기 김포",
        "경기 고양", "경기 파주",
    ],
    "인천": [
        "인천 중구", "인천 동구", "인천 미추홀", "인천 연수",
        "인천 남동", "인천 부평", "인천 계양", "인천 서구", "인천 강화",
    ],
    "강원": [
        "강원 춘천", "강원 원주", "강원 강릉", "강원 동해",
        "강원 속초", "강원 삼척", "강원 홍천", "강원 평창",
    ],
    "대구경북": [
        "대구 중구", "대구 수성", "대구 달서", "대구 북구",
        "경북 포항", "경북 경주", "경북 안동", "경북 구미",
    ],
    "대전충청": [
        "대전 중구", "대전 서구", "대전 유성",
        "충남 천안", "충남 아산", "충남 공주",
        "충북 청주", "충북 충주", "세종",
    ],
    "전북": [
        "전북 전주", "전북 익산", "전북 군산", "전북 정읍",
        "전북 남원", "전북 김제",
    ],
    "광주전남": [
        "광주 동구", "광주 서구", "광주 남구", "광주 북구", "광주 광산",
        "전남 목포", "전남 여수", "전남 순천", "전남 나주", "전남 해남",
    ],
    "부산경남서부": [
        "부산 사하", "부산 사상", "부산 강서", "부산 북구",
        "경남 창원", "경남 김해", "경남 진주", "경남 거제",
    ],
    "부산경남동부": [
        "부산 해운대", "부산 수영", "부산 남구", "부산 동래", "부산 금정",
        "경남 양산", "울산 남구", "울산 중구",
    ],
}


REGION_RSS_MAP: dict[str, str] = {
    "강원": "https://www.kwnews.co.kr/rss/allArticle.xml",
    "대구경북": "https://news.imaeil.com/rss/all.xml",
    "부산경남서부": "https://www.busan.com/rss/news.xml",
    "부산경남동부": "https://www.busan.com/rss/news.xml",
    "전북": "https://www.domin.co.kr/rss/allArticle.xml",
    "대전충청": "https://www.daejonilbo.com/rss/allArticle.xml",
}


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    if not s:
        return ""
    return html.unescape(_HTML_TAG_RE.sub("", s)).strip()


def _extract_sigungu_tokens(query: str) -> list[str]:
    """쿼리 '서울 강남' → ['서울', '강남'] / '세종' → ['세종']."""
    return [t for t in query.split() if t]


def _build_filter_tokens(region: str) -> set[str]:
    """권역 시군구명 1개라도 포함하면 통과시키는 필터 토큰 집합."""
    tokens: set[str] = set()
    for q in REGION_QUERY_MAP.get(region, []):
        for tok in _extract_sigungu_tokens(q):
            if len(tok) >= 2:
                tokens.add(tok)
    return tokens


def _matches_region(text: str, tokens: set[str]) -> str | None:
    """text 에 권역 토큰 1개라도 포함되면 매칭된 첫 시군구명 반환."""
    if not text:
        return None
    for tok in tokens:
        if tok in text:
            return tok
    return None


def _pick_local_area(title: str, summary: str, region: str) -> str:
    """제목/요약에서 권역 시군구명 1개 추출 → 시트 '지역' 컬럼용."""
    text = f"{title} {summary}"
    # 광역+기초 조합("서울 강남")을 우선 시도 → 단독 토큰 fallback
    for q in REGION_QUERY_MAP.get(region, []):
        if all(tok in text for tok in _extract_sigungu_tokens(q)):
            return q
    for q in REGION_QUERY_MAP.get(region, []):
        parts = _extract_sigungu_tokens(q)
        if not parts:
            continue
        last = parts[-1]
        if len(last) >= 2 and last in text:
            return q
    return region


def collect_naver_news(query: str, display: int = 30) -> list[dict]:
    """네이버 검색 API 호출. 키 없으면 명시적 에러."""
    client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()
    if not client_id or client_id == "PLACEHOLDER" or not client_secret or client_secret == "PLACEHOLDER":
        raise ValueError("NAVER_CLIENT_ID/SECRET이 .env에 없습니다")

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "User-Agent": USER_AGENT,
    }
    params = {"query": query, "display": min(display, 100), "sort": "date"}
    try:
        resp = requests.get(NAVER_NEWS_API, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        print(f"⚠️ 네이버 API 실패 (query='{query}'): {e}")
        return []

    out: list[dict] = []
    for it in items:
        out.append({
            "title": _strip_html(it.get("title", "")),
            "summary": _strip_html(it.get("description", "")),
            "link": it.get("link", "") or it.get("originallink", ""),
            "originallink": it.get("originallink", ""),
            "pubDate": it.get("pubDate", ""),
            "source": "네이버",
        })
    return out


def collect_local_paper_rss(rss_url: str) -> list[dict]:
    """지방지 RSS 수집. feedparser 미설치 시 빈 리스트."""
    if feedparser is None:
        print(f"⚠️ feedparser 미설치 — RSS 스킵: {rss_url}")
        return []
    try:
        d = feedparser.parse(rss_url, request_headers={"User-Agent": USER_AGENT})
        if getattr(d, "bozo", False) and not getattr(d, "entries", None):
            print(f"⚠️ RSS 파싱 실패 (entries 없음): {rss_url}")
            return []
        out: list[dict] = []
        for e in d.entries[:60]:
            out.append({
                "title": _strip_html(getattr(e, "title", "")),
                "summary": _strip_html(getattr(e, "summary", "") or getattr(e, "description", "")),
                "link": getattr(e, "link", ""),
                "originallink": getattr(e, "link", ""),
                "pubDate": getattr(e, "published", "") or getattr(e, "updated", ""),
                "source": "지방지RSS",
            })
        return out
    except Exception as e:
        print(f"⚠️ RSS 수집 실패 ({rss_url}): {e}")
        return []


def _parse_pubdate(s: str) -> float:
    """다양한 형식의 pubDate → epoch (실패 시 0)."""
    if not s:
        return 0.0
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except Exception:
            continue
    return 0.0


def _collect_for_region_sync(region: str, target: int = 20) -> list[dict]:
    queries = REGION_QUERY_MAP.get(region, [])
    if not queries:
        print(f"⚠️ 권역 매핑 없음: {region}")
        return []

    raw: list[dict] = []
    # 권역명 자체를 메인 쿼리로 1회 호출
    try:
        raw.extend(collect_naver_news(region, display=20))
    except ValueError:
        raise  # API 키 없음은 상위로 전파

    # 시군구 쿼리 (앞에서 N개)
    for q in queries[: min(len(queries), 8)]:
        raw.extend(collect_naver_news(q, display=10))

    rss_url = REGION_RSS_MAP.get(region)
    if rss_url:
        raw.extend(collect_local_paper_rss(rss_url))

    # URL 기반 dedup
    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for item in raw:
        url = (item.get("link") or item.get("originallink") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)

    # 권역 시군구명 1개 이상 포함 필터
    tokens = _build_filter_tokens(region)
    filtered: list[dict] = []
    for item in deduped:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        if _matches_region(text, tokens):
            filtered.append(item)

    # 최신순 정렬
    filtered.sort(key=lambda x: _parse_pubdate(x.get("pubDate", "")), reverse=True)

    return filtered[:MAX_PER_REGION]


async def collect_for_region(region: str, target: int = 20) -> list[dict]:
    return await asyncio.to_thread(_collect_for_region_sync, region, target)


async def collect_all_regions() -> dict[str, list[dict]]:
    """12권역 병렬 수집."""
    regions = list(REGION_QUERY_MAP.keys())
    print(f"📰 뉴스 수집 시작 — {len(regions)}개 권역")
    started = time.time()

    results = await asyncio.gather(
        *(collect_for_region(r) for r in regions),
        return_exceptions=True,
    )

    out: dict[str, list[dict]] = {}
    for region, res in zip(regions, results):
        if isinstance(res, Exception):
            print(f"❌ 수집 실패 [{region}]: {res}")
            out[region] = []
            continue
        out[region] = res
        print(f"  ✓ {region}: {len(res)}건")
    print(f"📰 뉴스 수집 완료 ({time.time() - started:.1f}s)")
    return out


# ── Google Sheets ──────────────────────────────────────────────────────────────

def _get_gspread_client():
    import gspread
    return gspread.service_account(filename="serviceAccountKey.json")


def _get_sheets_api():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    scopes = config.get("google_scopes", [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    creds = Credentials.from_service_account_file("serviceAccountKey.json", scopes=scopes)
    return build("sheets", "v4", credentials=creds)


def _ensure_worksheet(spreadsheet, title: str, headers: list[str]):
    """워크시트 없으면 생성 + 헤더 작성. 있으면 헤더 검증/보강."""
    try:
        ws = spreadsheet.worksheet(title)
    except Exception:
        ws = spreadsheet.add_worksheet(title=title, rows=200, cols=max(10, len(headers)))
        ws.update("A1", [headers])
        print(f"✅ 워크시트 생성: {title}")
        return ws, True

    first_row = ws.row_values(1)
    if not first_row or first_row[: len(headers)] != headers:
        ws.update("A1", [headers])
        print(f"✅ 워크시트 헤더 갱신: {title}")
    return ws, False


def _apply_checkbox_validation(api, spreadsheet_id: str, sheet_id: int,
                               start_row: int, end_row: int):
    """A열(idx 0) 지정 행 범위에 체크박스 DataValidation 일괄 적용."""
    body = {
        "requests": [
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1,
                    },
                    "rule": {
                        "condition": {"type": "BOOLEAN"},
                        "strict": True,
                    },
                }
            }
        ]
    }
    try:
        api.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()
    except Exception as e:
        print(f"⚠️ 체크박스 적용 실패: {e}")


def save_candidates_to_sheet(candidates: dict[str, list[dict]],
                             region_to_tribe: dict[str, str]) -> dict[str, Any]:
    """후보 시트에 일괄 추가. 각 행 카테고리 자동 태깅 + A열 체크박스.

    region_to_tribe: {"강원": "빌립", ...} — 시트 '지파' 컬럼 채우기용.
    반환: {"appended": N, "by_region": {...}}
    """
    spreadsheet_id = (config.get("news_clipping", {}) or {}).get("spreadsheet_id", "")
    if not spreadsheet_id or spreadsheet_id == "사용자_제공_예정_PLACEHOLDER":
        raise ValueError("news_clipping.spreadsheet_id 가 config.json 에 설정되지 않았습니다")

    gc = _get_gspread_client()
    ss = gc.open_by_key(spreadsheet_id)
    ws, _ = _ensure_worksheet(ss, CANDIDATE_SHEET, CANDIDATE_HEADERS)

    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    rows: list[list[Any]] = []
    by_region: dict[str, int] = {}
    for region, items in candidates.items():
        tribe = region_to_tribe.get(region, "")
        for it in items:
            title = it.get("title", "")
            summary = it.get("summary", "")
            link = it.get("link", "") or it.get("originallink", "")
            source = it.get("source", "")
            local_area = _pick_local_area(title, summary, region)
            cat = categorize(title, summary)
            rows.append([
                False, region, tribe, local_area, cat,
                title, summary, link, source, now_str,
            ])
        by_region[region] = len(items)

    if not rows:
        print("⚠️ 저장할 뉴스 후보 없음")
        return {"appended": 0, "by_region": by_region}

    existing = ws.row_count
    start_row_idx = len(ws.col_values(1))  # 0-based: 헤더(1행) 다음부터
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    end_row_idx = start_row_idx + len(rows)

    api = _get_sheets_api()
    _apply_checkbox_validation(api, spreadsheet_id, ws.id, start_row_idx, end_row_idx)

    print(f"✅ 후보 시트 저장: {len(rows)}건 (행 {start_row_idx + 1} ~ {end_row_idx})")
    _ = existing  # avoid unused warning in some linters
    return {"appended": len(rows), "by_region": by_region}
