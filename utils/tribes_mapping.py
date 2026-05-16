"""
GAbongAI 12지파 79개 지부 매핑 마스터 데이터.

양방향 매핑 지원:
- 구 양식: 지파명 + 교회명 (예: "요한지파 수지교회")
- 신 양식: 연합회 + 지부명 (예: "서울경기남부 용인지부")

import 시점에 alias 충돌을 assert 로 강제 검증 — 잘못된 데이터로는 봇 시작 자체가 실패.
"""

from typing import TypedDict


class BranchEntry(TypedDict):
    church: str          # 정식 교회명 (예: "수지교회")
    branch: str          # 정식 지부명 (예: "용인지부")
    tribe: str           # 지파명 (예: "요한")
    tribe_full: str      # "요한지파"
    union: str           # 연합회명 (예: "서울경기남부")
    union_full: str      # "서울경기남부 연합회"
    aliases: list[str]   # 충돌 없는 부분 매칭용


# alias 등록 원칙:
# - 다른 지부와 겹치지 않는 토큰만 등록
# - 충돌 위험 alias 의도적 제외: "부산"(부산교회 vs 부산야고보), "남양주"(빌립 vs 서야 구리남양주),
#   "야고보"(부산야고보 vs 서울야고보), 한 글자 토큰("동"/"남"/"서") 등
# - 풀네임(교회명/지부명)은 자동 등록되므로 aliases 에 중복 입력 X

TRIBES: dict[str, dict] = {
    "요한": {
        "union": "서울경기남부",
        "branches": [
            {"church": "과천교회",   "branch": "과천지부",     "aliases": ["과천"]},
            {"church": "성남교회",   "branch": "성남지부",     "aliases": ["성남"]},
            {"church": "강동교회",   "branch": "강동지부",     "aliases": ["강동"]},
            {"church": "수원교회",   "branch": "수원지부",     "aliases": ["수원"]},
            {"church": "안산교회",   "branch": "안산지부",     "aliases": ["안산"]},
            {"church": "평택교회",   "branch": "평택지부",     "aliases": ["평택"]},
            {"church": "이천교회",   "branch": "이천지부",     "aliases": ["이천"]},
            {"church": "수지교회",   "branch": "용인지부",     "aliases": ["수지", "용인"]},
            {"church": "왕십리교회", "branch": "성동지부",     "aliases": ["왕십리", "성동"]},
            {"church": "동탄교회",   "branch": "화성·동탄지부", "aliases": ["동탄", "화성동탄", "화성"]},
            {"church": "하남교회",   "branch": "하남지부",     "aliases": ["하남"]},
        ],
    },
    "베드로": {
        "union": "광주전남",
        "branches": [
            {"church": "광주교회", "branch": "광주지부", "aliases": ["광주"]},
            {"church": "목포교회", "branch": "목포지부", "aliases": ["목포"]},
            {"church": "여수교회", "branch": "여수지부", "aliases": ["여수"]},
            {"church": "순천교회", "branch": "순천지부", "aliases": ["순천"]},
            {"church": "송하교회", "branch": "송하지부", "aliases": ["송하"]},
            {"church": "광양교회", "branch": "광양지부", "aliases": ["광양"]},
            {"church": "해남교회", "branch": "해남지부", "aliases": ["해남"]},
            {"church": "나주교회", "branch": "나주지부", "aliases": ["나주"]},
        ],
    },
    "부산야고보": {
        "union": "부산경남서부",
        "branches": [
            # "부산" 단독 alias 제외: 부산교회/부산서부지부 vs 부산야고보지파 모호
            {"church": "부산교회", "branch": "부산서부지부", "aliases": ["부산서부"]},
            {"church": "마산교회", "branch": "마산지부",   "aliases": ["마산"]},
            {"church": "진해교회", "branch": "진해지부",   "aliases": ["진해"]},
            {"church": "거제교회", "branch": "거제지부",   "aliases": ["거제"]},
            {"church": "양산교회", "branch": "양산지부",   "aliases": ["양산"]},
            {"church": "통영교회", "branch": "통영지부",   "aliases": ["통영"]},
        ],
    },
    "안드레": {
        "union": "부산경남동부",
        "branches": [
            {"church": "울산교회", "branch": "울산지부", "aliases": ["울산"]},
            {"church": "진주교회", "branch": "진주지부", "aliases": ["진주"]},
            {"church": "창원교회", "branch": "창원지부", "aliases": ["창원"]},
            {"church": "제주교회", "branch": "제주지부", "aliases": ["제주"]},
            {"church": "김해교회", "branch": "김해지부", "aliases": ["김해"]},
        ],
    },
    "다대오": {
        "union": "대구경북",
        "branches": [
            {"church": "대구교회", "branch": "대구지부", "aliases": ["대구"]},
            {"church": "포항교회", "branch": "포항지부", "aliases": ["포항"]},
            {"church": "구미교회", "branch": "구미지부", "aliases": ["구미"]},
            {"church": "경주교회", "branch": "경주지부", "aliases": ["경주"]},
            {"church": "안동교회", "branch": "안동지부", "aliases": ["안동"]},
        ],
    },
    "빌립": {
        "union": "강원지역",
        "branches": [
            {"church": "원주교회",   "branch": "원주지부",   "aliases": ["원주"]},
            {"church": "동해교회",   "branch": "동해지부",   "aliases": ["동해"]},
            {"church": "강릉교회",   "branch": "강릉지부",   "aliases": ["강릉"]},
            {"church": "춘천교회",   "branch": "춘천지부",   "aliases": ["춘천"]},
            {"church": "속초교회",   "branch": "속초지부",   "aliases": ["속초"]},
            {"church": "충주교회",   "branch": "충주지부",   "aliases": ["충주"]},
            {"church": "제천교회",   "branch": "제천지부",   "aliases": ["제천"]},
            {"church": "청평교회",   "branch": "청평지부",   "aliases": ["청평"]},
            # "남양주" 단독 alias 제외: 서울야고보 구리남양주지부와 모호
            {"church": "남양주교회", "branch": "남양주지부", "aliases": []},
            {"church": "양평교회",   "branch": "양평지부",   "aliases": ["양평"]},
        ],
    },
    "시몬": {
        "union": "서울경기북부",
        "branches": [
            {"church": "화정교회",   "branch": "고양지부",   "aliases": ["화정", "고양"]},
            {"church": "서대문교회", "branch": "서대문지부", "aliases": ["서대문"]},
            {"church": "파주교회",   "branch": "파주지부",   "aliases": ["파주"]},
            {"church": "남산교회",   "branch": "남산지부",   "aliases": ["남산"]},
            {"church": "불광교회",   "branch": "은평지부",   "aliases": ["불광", "은평"]},
        ],
    },
    "바돌로매": {
        "union": "서울경기서부",
        "branches": [
            {"church": "영등포교회", "branch": "동작지부", "aliases": ["영등포", "동작"]},
            {"church": "부천교회",   "branch": "부천지부", "aliases": ["부천"]},
            {"church": "화곡교회",   "branch": "강서지부", "aliases": ["화곡", "강서"]},
            {"church": "김포교회",   "branch": "김포지부", "aliases": ["김포"]},
            {"church": "광명교회",   "branch": "광명지부", "aliases": ["광명"]},
        ],
    },
    "마태": {
        "union": "인천",
        "branches": [
            {"church": "인천교회",   "branch": "인천지부",   "aliases": ["인천"]},
            {"church": "서인천교회", "branch": "서인천지부", "aliases": ["서인천"]},
            {"church": "만수교회",   "branch": "남동지부",   "aliases": ["만수", "남동"]},
            {"church": "주안교회",   "branch": "주안지부",   "aliases": ["주안"]},
            {"church": "연수교회",   "branch": "연수지부",   "aliases": ["연수"]},
            {"church": "계양교회",   "branch": "계양지부",   "aliases": ["계양"]},
            {"church": "제물포교회", "branch": "동인천지부", "aliases": ["제물포", "동인천"]},
        ],
    },
    "맛디아": {
        "union": "대전충청",
        "branches": [
            {"church": "대전교회", "branch": "대전지부", "aliases": ["대전"]},
            {"church": "천안교회", "branch": "천안지부", "aliases": ["천안"]},
            {"church": "청주교회", "branch": "청주지부", "aliases": ["청주"]},
            {"church": "서산교회", "branch": "서산지부", "aliases": ["서산"]},
            {"church": "공주교회", "branch": "공주지부", "aliases": ["공주"]},
            {"church": "아산교회", "branch": "아산지부", "aliases": ["아산"]},
            {"church": "세종교회", "branch": "세종지부", "aliases": ["세종"]},
            {"church": "논산교회", "branch": "논산지부", "aliases": ["논산"]},
        ],
    },
    "서울야고보": {
        "union": "서울경기동부",
        "branches": [
            {"church": "서울교회",   "branch": "서울지부",       "aliases": ["서울"]},
            {"church": "포천교회",   "branch": "포천지부",       "aliases": ["포천"]},
            # "남양주" alias 제외: 빌립 남양주지부와 모호. "구리"는 안전.
            {"church": "구리교회",   "branch": "구리남양주지부", "aliases": ["구리"]},
            {"church": "동대문교회", "branch": "동대문지부",     "aliases": ["동대문"]},
            {"church": "의정부교회", "branch": "의정부지부",     "aliases": ["의정부"]},
        ],
    },
    "도마": {
        "union": "전북",
        "branches": [
            {"church": "전주교회", "branch": "전주지부", "aliases": ["전주"]},
            {"church": "익산교회", "branch": "익산지부", "aliases": ["익산"]},
            {"church": "군산교회", "branch": "군산지부", "aliases": ["군산"]},
            {"church": "정읍교회", "branch": "정읍지부", "aliases": ["정읍"]},
        ],
    },
}


def _build_branches() -> list[BranchEntry]:
    out: list[BranchEntry] = []
    for tribe_name, t in TRIBES.items():
        for b in t["branches"]:
            out.append({
                "church": b["church"],
                "branch": b["branch"],
                "tribe": tribe_name,
                "tribe_full": tribe_name + "지파",
                "union": t["union"],
                "union_full": t["union"] + " 연합회",
                "aliases": list(b.get("aliases", [])),
            })
    return out


BRANCHES: list[BranchEntry] = _build_branches()


def _norm_key(s: str) -> str:
    # 공백 + 가운뎃점(·) 제거. 정식명에 가운뎃점 들어가는 케이스("화성·동탄지부") 흡수.
    return s.replace(" ", "").replace("·", "").strip()


def _build_reverse_index() -> dict[str, BranchEntry]:
    """입력 토큰 -> branch entry 정방향 lookup. 충돌 시 assert 실패."""
    idx: dict[str, BranchEntry] = {}

    def _add(key: str, entry: BranchEntry, kind: str):
        norm = _norm_key(key)
        if not norm:
            return
        if norm in idx and idx[norm]["branch"] != entry["branch"]:
            raise AssertionError(
                f"alias 충돌 ({kind}): '{key}' (norm='{norm}') "
                f"이미 '{idx[norm]['branch']}' 매핑 — '{entry['branch']}' 추가 거부"
            )
        idx[norm] = entry

    for entry in BRANCHES:
        _add(entry["church"], entry, "church")
        _add(entry["branch"], entry, "branch")
        for alias in entry["aliases"]:
            _add(alias, entry, "alias")
    return idx


REVERSE_INDEX: dict[str, BranchEntry] = _build_reverse_index()


# 지파/연합회 명 셋 (양식 첫 토큰 매칭용)
TRIBE_NAMES: set[str] = set(TRIBES.keys()) | {t + "지파" for t in TRIBES.keys()}
UNION_NAMES: set[str] = (
    {t["union"] for t in TRIBES.values()}
    | {t["union"] + " 연합회" for t in TRIBES.values()}
    | {t["union"] + "연합회" for t in TRIBES.values()}
)
TRIBE_TO_UNION: dict[str, str] = {t: TRIBES[t]["union"] for t in TRIBES}
UNION_TO_TRIBE: dict[str, str] = {TRIBES[t]["union"]: t for t in TRIBES}


# Import-time 검증
assert len(BRANCHES) == 79, f"79개 지부 예상, 실제 {len(BRANCHES)}개"
assert len({b["branch"] for b in BRANCHES}) == 79, "지부명 중복"
assert len({b["church"] for b in BRANCHES}) == 79, "교회명 중복"
assert len(TRIBES) == 12, f"12지파 예상, 실제 {len(TRIBES)}개"
assert len(UNION_TO_TRIBE) == 12, "연합회 중복"
