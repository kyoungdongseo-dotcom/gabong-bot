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
    """라벨 앞 이모지·불릿 기호·번호+점 제거"""
    text = clean_emoji(text)
    text = re.sub(r'^[\s■▪◆▶•\-\*]+', '', text)
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
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
        kv = parse_kv_line(stripped)
        if kv:
            key_raw, val = kv
            norm = _normalize(key_raw)
            if norm in alias_map:
                current_field = alias_map[norm]
                result[current_field] = val
            else:
                # 알 수 없는 키 → 현재 필드 이어붙이기
                if current_field:
                    result[current_field] += ' ' + stripped
        else:
            # 콜론 없음 → 이전 필드 다음 줄로 이어붙이기
            if current_field:
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
