"""
지파/지부 입력 정규화 + 검증 헬퍼.

핵심 API:
- resolve(text): 단일 토큰 -> BranchEntry | None (정확 매칭)
- resolve_pair(first, second): 두 토큰 조합 -> BranchEntry | None
- validate_pair(first, second): (BranchEntry | None, error_msg | None) — 잘못된 조합 친화적 오류
- suggest(text): difflib 기반 오타 후보 ["수지교회", ...]
"""

from difflib import get_close_matches

from utils.tribes_mapping import (
    BRANCHES,
    REVERSE_INDEX,
    TRIBE_NAMES,
    UNION_NAMES,
    BranchEntry,
    _norm_key,
)


# ── 정확 매칭 ─────────────────────────────────────────────────────────────

def resolve(text: str) -> BranchEntry | None:
    """단일 입력 텍스트로 지부 lookup. 공백/가운뎃점 무시. 정확 매칭만."""
    if not text:
        return None
    return REVERSE_INDEX.get(_norm_key(text))


def resolve_pair(first: str, second: str) -> BranchEntry | None:
    """두 토큰 입력 — 각각 resolve 후 동일 지부면 반환, 다르면 None.
    한쪽만 매칭되면 그쪽 entry 반환 (사용자 친화).
    """
    a = resolve(first)
    b = resolve(second)
    if a and b:
        return a if a["branch"] == b["branch"] else None
    return a or b


# ── 지파/연합회 토큰 판별 ────────────────────────────────────────────────

_NORM_TRIBE_NAMES = {_norm_key(t) for t in TRIBE_NAMES}
_NORM_UNION_NAMES = {_norm_key(u) for u in UNION_NAMES}


def is_tribe_token(text: str) -> bool:
    return _norm_key(text) in _NORM_TRIBE_NAMES


def is_union_token(text: str) -> bool:
    return _norm_key(text) in _NORM_UNION_NAMES


def _strip_tribe_suffix(s: str) -> str:
    n = _norm_key(s)
    if n.endswith("지파"):
        n = n[:-2]
    return n


def _strip_union_suffix(s: str) -> str:
    n = _norm_key(s)
    if n.endswith("연합회"):
        n = n[:-3]
    return n


# ── 검증 (잘못된 조합 감지) ──────────────────────────────────────────────

def validate_pair(first: str, second: str) -> tuple[BranchEntry | None, str | None]:
    """첫줄 두 토큰 검증.

    예: ("요한지파", "수지교회") -> (entry, None)
        ("요한지파", "광주교회") -> (None, "...광주교회는 베드로지파...")
        ("서울경기남부", "용인지부") -> (entry, None)
        ("수지교회",) -> single-token fallback 은 호출자 책임

    반환: (BranchEntry | None, error_message | None)
    """
    first_is_tribe = is_tribe_token(first)
    first_is_union = is_union_token(first)

    # 케이스 1: 첫 토큰이 지파/연합회 — 두번째 토큰을 교회/지부로 lookup
    if first_is_tribe or first_is_union:
        entry = resolve(second)
        if not entry:
            sug = suggest(second, n=1)
            err = f"'{second}' 교회/지부명을 찾을 수 없습니다."
            if sug:
                err += f" 혹시 '{sug[0]}'?"
            return None, err

        if first_is_tribe:
            expected = _strip_tribe_suffix(first)
            if expected != entry["tribe"]:
                return None, (
                    f"'{first} {second}' 조합이 맞지 않습니다.\n"
                    f"{entry['church']}는 {entry['tribe_full']} 소속입니다."
                )
        if first_is_union:
            expected = _strip_union_suffix(first)
            if expected != _norm_key(entry["union"]):
                return None, (
                    f"'{first} {second}' 조합이 맞지 않습니다.\n"
                    f"{entry['branch']}는 {entry['union']} 연합회 소속입니다."
                )
        return entry, None

    # 케이스 2: 두 토큰 모두 교회/지부 후보
    a = resolve(first)
    b = resolve(second)
    if a and b:
        if a["branch"] == b["branch"]:
            return a, None
        return None, (
            f"'{first}'({a['tribe_full']} {a['branch']})와 "
            f"'{second}'({b['tribe_full']} {b['branch']}) — 서로 다른 지부입니다.\n"
            f"양식을 확인해 주세요."
        )
    if a or b:
        return a or b, None

    # 케이스 3: 매칭 실패 — 양쪽에서 추천
    sug = suggest(first, n=1) or suggest(second, n=1)
    err = f"지파/연합회/교회/지부명 인식 실패: '{first} {second}'"
    if sug:
        err += f" 혹시 '{sug[0]}'?"
    return None, err


# ── 오타 추천 (difflib) ──────────────────────────────────────────────────

# 추천 후보: 정식 교회명/지부명/지파full/union_full (alias 제외 — 정식명만 제안)
def _build_suggest_candidates() -> dict[str, str]:
    """norm -> 정식명. difflib 검색용."""
    out: dict[str, str] = {}
    for e in BRANCHES:
        out[_norm_key(e["church"])] = e["church"]
        out[_norm_key(e["branch"])] = e["branch"]
    for t in TRIBE_NAMES:
        out[_norm_key(t)] = t
    for u in UNION_NAMES:
        out[_norm_key(u)] = u
    return out


_SUGGEST_CANDIDATES: dict[str, str] = _build_suggest_candidates()


def suggest(text: str, n: int = 2, cutoff: float = 0.7) -> list[str]:
    """difflib 기반 오타 후보. 정식명 반환."""
    key = _norm_key(text or "")
    if not key:
        return []
    matches = get_close_matches(key, list(_SUGGEST_CANDIDATES.keys()), n=n, cutoff=cutoff)
    return [_SUGGEST_CANDIDATES[m] for m in matches]
