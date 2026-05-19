"""
Google Workspace Shared Drive 폴더 ID 매핑.

구조: 12연합회 × 5종 보고서 = 60개 폴더 (평면, 지부/월 하위 없음)
- Shared Drive: 신천지자원봉사단(12지파)
- Root: "신천지자원봉사단(12지파)" 폴더

tribes_mapping.union 과 키 일관성:
- DRIVE_FOLDERS 키 "강원" ↔ tribes_mapping "강원지역" (UNION_ALIAS 로 정규화)
- 나머지 11개는 정확 일치

사용 예:
    from utils.drive_folders import get_folder_id
    from utils.tribe_resolver import resolve
    entry = resolve("수지교회")           # BranchEntry
    fid = get_folder_id(entry["union"], "volunteer")
"""

SHARED_DRIVE_ID = "0AHk7QZPrlfcVUk9PVA"
ROOT_FOLDER_ID = "16q4WKIbqYmy3_CsnWj9ZqKJojWIwuEha"

# 12연합회 × 5종 = 60개 폴더 (사용자 확정 매핑, 2026-05-19)
DRIVE_FOLDERS: dict[str, dict[str, str]] = {
    "서울경기남부": {
        "1_봉사활동보고서": "1IoddoD4FVqD3PA-0glfJBWJ3chyzgdnW",
        "2_언론보도보고서": "1JTU0gvglP6zCEu00c75KyzZSq-_130AB",
        "3_수상보고서":    "1Yrly3RyCr1vX04XPJmMZdrqdg3-izNHn",
        "4_협약보고서":    "1Pxu8XPR2AccsScqGk2xau1OHM4lCSy6J",
        "5_해외봉사보고서": "1-UjGJ9sPCFQzes0ArJwn1GTAql1ppgkt",
    },
    "광주전남": {
        "1_봉사활동보고서": "1wJYPwKUFVXrdJANM5wddd1GznyoQFxX-",
        "2_언론보도보고서": "1imvJdVf3-W-IeV2TxHv8Mm8PQcLENrl2",
        "3_수상보고서":    "1-E97GSmCmRsGderLqDqeihtDleFtbF7l",
        "4_협약보고서":    "1RRvM_bp7f3GU8ultUFXDXdmEXd_qa6oT",
        "5_해외봉사보고서": "1KfKoZ5O37IXQWLWQg6PB2g-OFHRBFAqi",
    },
    "부산경남서부": {
        "1_봉사활동보고서": "14VZdcaiQts7AFYCldD194KFFpStabZlc",
        "2_언론보도보고서": "1XaEvGdoZCxi7aAj7p0f_nl8I1Mk6k9I8",
        "3_수상보고서":    "1zai9T3yIciocJjWActOLSonu8pKeNCTm",
        "4_협약보고서":    "1bsXINdq_3JvC1gGYj538-RaobdUZdY75",
        "5_해외봉사보고서": "1VDV86m_h2a0KG1HlTbo_qtUtiD-VmZt8",
    },
    "부산경남동부": {
        "1_봉사활동보고서": "1d2lej-hil27hsqCI4fqvd8OCEIZBhUkz",
        "2_언론보도보고서": "1j1KGU6pf5bJnq4MF3kmwnP_JSUwwUnBY",
        "3_수상보고서":    "1wwQn9h7zkxh72V5n4XiOzykGJWuki4yy",
        "4_협약보고서":    "1gAASIawYxg3SwZA7fRpaDHnctCsioWO7",
        "5_해외봉사보고서": "1i-FLzoS_3u8khjj7qPa_6VPVLm-_kHCv",
    },
    "대구경북": {
        "1_봉사활동보고서": "1HDzzMB2Bvy-SFYpRVoZkuNp4ABvUif1W",
        "2_언론보도보고서": "1xFJmlhbxmkTNr8geX0hTe0ybiwQrRMLc",
        "3_수상보고서":    "1DeP-nhzwGbsxl9HDxCwsDy7_gucQPR4p",
        "4_협약보고서":    "1c_Qz3Nh0KErVLGwxbKyetfHwaMcxiha4",
        "5_해외봉사보고서": "1gyzdwdboy1iKdsnOBtHtGgUwsOAGdWB3",
    },
    "강원": {
        "1_봉사활동보고서": "1j_zyh9guIvsskLEjsHo-ACqhtXgbYXOa",
        "2_언론보도보고서": "1pgrTxmbIpB2DnayAdqQRCjZ2lUEFNl_-",
        "3_수상보고서":    "1yFaOuRLet1-YcV1KPh8SFycFLOU1Zchf",
        "4_협약보고서":    "1z7EObhcBrc9OGUk_ImgH3bmiVCbWah_m",
        "5_해외봉사보고서": "1r91XFTefxN9IG6-RqPMe7Z6vUzJPrso5",
    },
    "서울경기북부": {
        "1_봉사활동보고서": "1q5VIrjCnhO8F4UWpyyiDJ3diNtmxgfhR",
        "2_언론보도보고서": "1jLpU-klIJUfKuZWRzP9bVze61l2fUCO0",
        "3_수상보고서":    "1fISyW6qi1smcJWP-QJqqanjOb4j4RjME",
        "4_협약보고서":    "1D2he8zIEDTg67Izp_1DC4owNaZDtk_WS",
        "5_해외봉사보고서": "1z7ZXQnw_qzYq-rbIty2xeDPFp3uXTfAg",
    },
    "서울경기서부": {
        "1_봉사활동보고서": "1ztHQixFrd8SpnuYtd5Gzur9ssAheDLHw",
        "2_언론보도보고서": "14Dc-08URVa48n8Bn0qP-zKQjvR3Rnf8z",
        "3_수상보고서":    "1rzrrrL90y7bu1unXqaSSOeN3_QpEF7T2",
        "4_협약보고서":    "1ptsbfdGIWfqJ5mMFB_VQFmPTAeb3gFIY",
        "5_해외봉사보고서": "1C_YnU4fEsSTseewjxg4e_aTGvuaeDPrQ",
    },
    "인천": {
        "1_봉사활동보고서": "1BIDo39isfN4uvw19TyW4fIWQrJEhI9Og",
        "2_언론보도보고서": "1h-6Ej2mBkZ8Ns7IfUgo4XClnmTv0hY-E",
        "3_수상보고서":    "1EnPYP7fw9JJrrRtsJko6kaSO-eZmuH8A",
        "4_협약보고서":    "1JGKJKukq6-Dh5M0aGdI-5ZcB2SAVd8mC",
        "5_해외봉사보고서": "1Pom6a31UkMxqVOiPUyIeQ_yoy0MAKRQX",
    },
    "대전충청": {
        "1_봉사활동보고서": "1Cna0v_J5jnbi0JSBw79bhDC-8kmY7so6",
        "2_언론보도보고서": "12Pybo5zLO7RPDya5apI5isIpvaBWqGSi",
        "3_수상보고서":    "1luGg7AAIPM2RqiRPssHLZnmv09ut3jg5",
        "4_협약보고서":    "14qYpNT0A1jfIoyRVORXaM1Vb_jql55Rg",
        "5_해외봉사보고서": "1-Um34MsCmDeCuCb7bnpxu_Fshs24iqJE",
    },
    "서울경기동부": {
        "1_봉사활동보고서": "1X1oNQci8Cye6XlFE6YpUA9a3nKD4nla8",
        "2_언론보도보고서": "1B40RwzZpLIoc_6GXUwJpA_IDEalDmXFT",
        "3_수상보고서":    "1ZJ5eFqmX1dSNdsNtbVYlYO-XGs6C-R6W",
        "4_협약보고서":    "1TRHrsxw37weoJJrFBW8mvy-Kn0XTqGSS",
        "5_해외봉사보고서": "1AjsTLp9FNtJSZyQ3d9Finq2gQjLtt1q8",
    },
    "전북": {
        "1_봉사활동보고서": "1Neyj-zhkF2VEfYoKAfk89qKYfqgNrtno",
        "2_언론보도보고서": "1SaIlL8o_NUKDOL74i69t0jd7CaAl8qNn",
        "3_수상보고서":    "1pz0gplS6wxbrl2Ldd8rkwruMW_220Tp1",
        "4_협약보고서":    "1EvwzWOV9S2mDtlrhqLO7AxhUlaUI6eE8",
        "5_해외봉사보고서": "1-cyz9Vr5ED31HYKRNTlHbxFFfs156Acs",
    },
}

# tribes_mapping union 명 → DRIVE_FOLDERS 키 정규화
# 현재 1건만 차이: "강원지역" → "강원"
UNION_ALIAS: dict[str, str] = {
    "강원지역": "강원",
}

# 보고서 타입 → DRIVE_FOLDERS sub-key
REPORT_TYPE_TO_FOLDER: dict[str, str] = {
    "volunteer": "1_봉사활동보고서",   # 봉사 (Phase 2 우선)
    "press":     "2_언론보도보고서",   # 언론보도
    "award":     "3_수상보고서",       # 수상
    "mou":       "4_협약보고서",       # MOU
    "overseas":  "5_해외봉사보고서",   # 해외봉사 (비활성)
}


def normalize_union(union: str) -> str:
    """tribes_mapping 의 union 명을 DRIVE_FOLDERS 키 형식으로 정규화."""
    return UNION_ALIAS.get(union, union)


def get_folder_id(union: str, report_type: str) -> str:
    """연합회 + 보고서 타입 → Drive 폴더 ID.

    Args:
        union: tribes_mapping 의 entry["union"] 또는 DRIVE_FOLDERS 키
        report_type: "volunteer" | "press" | "award" | "mou" | "overseas"

    Returns:
        Drive 폴더 ID (string)

    Raises:
        KeyError: union 또는 report_type 매핑 없을 때 (fail-fast, silent fail 차단)
    """
    norm = normalize_union(union)
    if norm not in DRIVE_FOLDERS:
        raise KeyError(
            f"Drive folder mapping 없음: union='{union}' (norm='{norm}'). "
            f"DRIVE_FOLDERS 또는 UNION_ALIAS 추가 필요."
        )
    sub = REPORT_TYPE_TO_FOLDER.get(report_type)
    if sub is None:
        raise KeyError(
            f"Drive report_type 매핑 없음: '{report_type}'. "
            f"허용: {list(REPORT_TYPE_TO_FOLDER.keys())}"
        )
    folder = DRIVE_FOLDERS[norm].get(sub)
    if not folder:
        raise KeyError(
            f"Drive 폴더 ID 없음: union='{norm}' report_type='{report_type}' (sub='{sub}')"
        )
    return folder


# Import-time 검증 (잘못된 데이터로 봇 시작 차단)
assert len(DRIVE_FOLDERS) == 12, f"12연합회 예상, 실제 {len(DRIVE_FOLDERS)}개"
for _u, _sub in DRIVE_FOLDERS.items():
    assert len(_sub) == 5, f"{_u}: 5종 보고서 폴더 예상, 실제 {len(_sub)}개"
    for _k, _fid in _sub.items():
        assert _fid and isinstance(_fid, str), f"{_u}/{_k} 폴더 ID 비어있음"

# tribes_mapping union 과의 일관성 검증 (정규화 후 12개 모두 DRIVE_FOLDERS 에 있어야 함)
try:
    from utils.tribes_mapping import TRIBES as _TRIBES
    _unions_in_mapping = {t["union"] for t in _TRIBES.values()}
    for _u in _unions_in_mapping:
        _norm = normalize_union(_u)
        assert _norm in DRIVE_FOLDERS, (
            f"tribes_mapping union '{_u}' (norm='{_norm}') 가 DRIVE_FOLDERS 에 없음. "
            f"UNION_ALIAS 추가 또는 DRIVE_FOLDERS 키 수정 필요."
        )
except ImportError:
    # tribes_mapping import 실패는 무시 (drive_folders 단독 테스트 허용)
    pass
