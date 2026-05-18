"""공통 보고서 파싱 유틸리티"""
import re


def clean_emoji(text: str) -> str:
    """이모지·변형 선택자·제로폭 문자 제거"""
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)   # 보충 평면 이모지
    text = re.sub(r'[☀-➿⬀-⯿]', '', text)  # 기타 기호
    text = re.sub(r'[︀-️]', '', text)            # 변형 선택자
    text = re.sub(r'[​-‍﻿]', '', text)      # 제로폭 문자
    return text


def clean_label(text: str) -> str:
    """라벨 앞 이모지·불릿 기호·번호+점 제거 + 괄호 안 보조 설명 제거.
    Why: 신규 봉사양식 라벨에 "(서기)", "(명)", "(지역문제점)" 등 메타 표기 흔함.
    이를 제거하지 않으면 alias 매칭 실패 (2026-05-18)."""
    text = clean_emoji(text)
    text = re.sub(r'^[\s■▪◆▶•\-\*]+', '', text)
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
    text = re.sub(r'\([^)]*\)', '', text)
    return text.strip()


def parse_kv_line(line: str) -> tuple[str, str] | None:
    """'키: 값' 파싱 — 전각·반각·특수 콜론 모두 지원"""
    m = re.match(r'^(.+?)\s*[：:∶]\s*(.*)', line)
    if m:
        return clean_label(m.group(1)), m.group(2).strip()
    return None


def _normalize(key: str) -> str:
    """내부 공백 제거 (수 상 명 → 수상명)"""
    return re.sub(r'\s+', '', key)


def parse_multiline_kv(text: str, key_aliases: dict) -> dict:
    """
    캡션을 키 별칭 기반으로 파싱. 다중 라인 값 자동 합치기.

    key_aliases: {"필드명": ["별칭1", "별칭2"]}
    반환: {"필드명": "값", ...}  (앞뒤 공백 정리)
    """
    alias_map: dict[str, str] = {}
    for field, aliases in key_aliases.items():
        for alias in aliases:
            alias_map[_normalize(alias)] = field

    result = {field: '' for field in key_aliases}
    current_field: str | None = None

    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            current_field = None
            continue
        # 불릿(■▪◆▶•) 시작 라인은 새 섹션 헤더로 취급 — 이전 필드 누적 방지
        # Why: "■ 현장 반응 (말한 표현 그대로 기록)" 같은 안내 라인이 직전 필드에
        #     누적되어 데이터 오염되는 문제 차단 (2026-05-18)
        is_bullet_line = bool(re.match(r'^[■▪◆▶•]', stripped))
        kv = parse_kv_line(stripped)
        if kv:
            key_raw, val = kv
            norm = _normalize(key_raw)
            if norm in alias_map:
                current_field = alias_map[norm]
                result[current_field] = val
            else:
                # 알 수 없는 키
                if is_bullet_line:
                    # 새 섹션 헤더로 보고 이전 필드 종료
                    current_field = None
                elif current_field:
                    result[current_field] += ' ' + stripped
        else:
            # 콜론 없음 — '■ 키(메타)값' 또는 '■ 키(메타)\n값' 패턴 처리 (2026-05-18)
            # Why: 사용자가 콜론 빼먹은 양식 흔함. "■ 활동 성과(수치데이터 포함)420L" 처럼
            #     괄호로 메타 표기 + 그 뒤 곧바로 값이 붙는 케이스 + 값 다음 줄 케이스.
            paren_match = (
                re.match(r'^([^()]+\([^)]*\))\s*(.*)$', stripped)
                if is_bullet_line and '(' in stripped else None
            )
            if paren_match:
                key_part = paren_match.group(1)
                val_part = paren_match.group(2).strip()
                norm = _normalize(clean_label(key_part))
                if norm in alias_map:
                    current_field = alias_map[norm]
                    result[current_field] = val_part  # 빈 문자열이면 다음 줄에서 채움
                    continue
            if is_bullet_line:
                current_field = None
            elif current_field:
                result[current_field] += '\n' + stripped

    return {k: v.strip() for k, v in result.items()}


def extract_first_line_meta(line: str, suffix_keywords: list) -> tuple[str, str]:
    """
    첫 줄에서 지역/지부 추출.

    suffix_keywords: 뒤에서 제거할 키워드 목록 (긴 것부터 시도)
    반환: (part1, part2)  — 공백으로 나눈 첫 두 토큰
    """
    clean = clean_emoji(line).strip()
    for kw in sorted(suffix_keywords, key=len, reverse=True):
        clean = re.sub(rf'\s*{re.escape(kw)}\s*$', '', clean).strip()
    parts = clean.split()
    return (parts[0] if parts else '', parts[1] if len(parts) >= 2 else '')
