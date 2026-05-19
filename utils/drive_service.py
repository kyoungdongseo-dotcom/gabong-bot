"""
Google Workspace Shared Drive 업로드 서비스 (옵션 B 비동기).

- 인증: serviceAccountKey.json 재사용 (기존 sheet 와 동일, drive scope 이미 포함)
- Shared Drive: supportsAllDrives=True 강제 (서비스 계정 storage=0 우회)
- 폴더: utils.drive_folders.DRIVE_FOLDERS 의 60개 폴더 ID 사용 (탐색 X)
- 재시도: 3회 지수 백오프 (0.5s → 1s → 2s)
- silent fail 차단: 모든 에러 print(flush=True) + admin DM (선택)
- 비동기: upload_docx_background() 가 asyncio task 안에서 안전 실행

Phase 2 범위: 봉사보고서 (volunteer) 만. MOU/수상은 동일 인터페이스로 추가.
"""

import asyncio
import os
import time
from typing import Optional

import config
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from utils.drive_folders import get_folder_id, normalize_union


# ── 싱글톤 service ─────────────────────────────────────────────────────────

_DRIVE_SERVICE = None


def get_drive_service():
    """Drive v3 service 싱글톤. config.google_scopes 재사용."""
    global _DRIVE_SERVICE
    if _DRIVE_SERVICE is None:
        creds = Credentials.from_service_account_file(
            'serviceAccountKey.json',
            scopes=config.get('google_scopes'),
        )
        _DRIVE_SERVICE = build('drive', 'v3', credentials=creds, cache_discovery=False)
        print("✅ Drive service 초기화 완료 (Shared Drive 모드)", flush=True)
    return _DRIVE_SERVICE


# ── 핵심 업로드 (동기) ─────────────────────────────────────────────────────

def _upload_once(local_path: str, filename: str, folder_id: str) -> dict:
    """Drive 업로드 1회 시도. 성공 시 {'id', 'webViewLink'} 반환, 실패 시 raise."""
    service = get_drive_service()
    media = MediaFileUpload(
        local_path,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        resumable=False,
    )
    body = {'name': filename, 'parents': [folder_id]}
    file = service.files().create(
        body=body,
        media_body=media,
        fields='id, webViewLink, name',
        supportsAllDrives=True,
    ).execute()
    return file


def upload_docx(local_path: str, filename: str, union: str, report_type: str) -> dict:
    """Drive 업로드 (동기, 재시도 3회 지수 백오프).

    Args:
        local_path: 업로드할 .docx 파일 절대경로
        filename: Drive 에 저장될 파일명 (예: "서울경기남부_용인지부_봉사_26_05_19.docx")
        union: tribes_mapping entry["union"] (예: "서울경기남부", "강원지역")
        report_type: "volunteer" | "press" | "award" | "mou" | "overseas"

    Returns:
        {'id': file_id, 'webViewLink': url, 'name': filename}

    Raises:
        FileNotFoundError: local_path 없음
        KeyError: union/report_type 매핑 없음
        HttpError: 3회 재시도 후에도 실패
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Drive 업로드 대상 파일 없음: {local_path}")

    folder_id = get_folder_id(union, report_type)  # fail-fast (KeyError)

    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            result = _upload_once(local_path, filename, folder_id)
            print(
                f"📤 Drive 업로드 OK: {filename} → folder={folder_id} "
                f"file_id={result['id']} (attempt={attempt + 1})",
                flush=True,
            )
            return result
        except HttpError as e:
            status = getattr(e.resp, 'status', None)
            # 4xx 권한/검증 에러는 재시도 무의미 (403 storageQuotaExceeded, 404 폴더 없음 등)
            if status in (400, 401, 403, 404):
                print(
                    f"❌ Drive 업로드 fail-fast (status={status}): {filename} — {e}",
                    flush=True,
                )
                raise
            last_err = e
            wait = 0.5 * (2 ** attempt)
            print(
                f"⚠️ Drive 업로드 재시도 {attempt + 1}/3 (status={status}, {wait}s 대기): {e}",
                flush=True,
            )
            time.sleep(wait)
        except Exception as e:
            last_err = e
            wait = 0.5 * (2 ** attempt)
            print(
                f"⚠️ Drive 업로드 예외 재시도 {attempt + 1}/3 ({wait}s 대기): {e}",
                flush=True,
            )
            time.sleep(wait)

    print(f"❌ Drive 업로드 최종 실패 (3회 재시도): {filename}", flush=True)
    raise last_err if last_err else RuntimeError("Drive 업로드 실패 (원인 미상)")


# ── 비동기 후처리 (옵션 B) ─────────────────────────────────────────────────

async def upload_docx_background(
    local_path: str,
    filename: str,
    union: str,
    report_type: str,
    *,
    cleanup: bool = True,
    admin_notify=None,
    user_id: Optional[int] = None,
) -> Optional[dict]:
    """봉사보고서 finalize 직후 백그라운드 task 로 호출. 봇 핵심 흐름 영향 0.

    - 성공: report_log 에 drive_uploaded/ok 기록 + Drive 링크 반환
    - 실패: report_log 에 drive_uploaded/fail 기록 + admin DM (선택)
    - cleanup=True 시 업로드 시도 후 local_path 삭제 (호출자가 cleanup 위임)

    Args:
        local_path: .docx 파일 경로
        filename: Drive 파일명
        union: 연합회명
        report_type: 보고서 타입
        cleanup: 업로드 후 local_path 삭제 여부 (호출자 보존 필요시 False)
        admin_notify: async fn(text) — 실패 시 admin DM 콜백 (None 이면 로그만)
        user_id: report_log 기록용

    Returns:
        업로드 성공 시 {'id', 'webViewLink', 'name'}, 실패 시 None.
    """
    from database import log_report_stage

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None, upload_docx, local_path, filename, union, report_type,
        )
        try:
            log_report_stage(
                report_type, 'drive_uploaded', 'ok',
                user_id=user_id,
                detail=f"file_id={result['id']}",
            )
        except Exception as log_e:
            print(f"⚠️ drive_uploaded 로그 기록 실패: {log_e}", flush=True)
        return result
    except Exception as e:
        try:
            log_report_stage(
                report_type, 'drive_uploaded', 'fail',
                user_id=user_id,
                detail=f"{type(e).__name__}: {str(e)[:180]}",
            )
        except Exception as log_e:
            print(f"⚠️ drive_uploaded(fail) 로그 기록 실패: {log_e}", flush=True)

        if admin_notify is not None:
            try:
                await admin_notify(
                    f"❌ Drive 업로드 실패\n"
                    f"파일: {filename}\n"
                    f"연합회: {union} / 타입: {report_type}\n"
                    f"에러: {type(e).__name__}: {str(e)[:200]}"
                )
            except Exception as dm_e:
                print(f"⚠️ Drive 실패 admin DM 발송 실패: {dm_e}", flush=True)
        return None
    finally:
        if cleanup and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as rm_e:
                print(f"⚠️ Drive 업로드 후 tmp 삭제 실패: {local_path} — {rm_e}", flush=True)


# ── 파일명 헬퍼 ────────────────────────────────────────────────────────────

def build_filename(union: str, branch: str, activity: str, date: str) -> str:
    """Drive 파일명 표준: [연합회]_[지부]_[활동명]_YY_MM_DD.docx

    - 활동명 50자 제한
    - Drive 금지 문자 (`/` 등) 치환
    - 공백 → `_`

    Args:
        union: "서울경기남부"
        branch: "용인지부"
        activity: "노인복지관 청소봉사"
        date: "2026-05-19" (YYYY-MM-DD) 또는 "26-05-19"

    Returns:
        "서울경기남부_용인지부_노인복지관_청소봉사_26_05_19.docx"
    """
    # union 정규화: "강원지역" → "강원" (DRIVE_FOLDERS 키와 파일명 일관성)
    union = normalize_union(union)
    # 날짜 정규화: YYYY-MM-DD → YY_MM_DD
    d = (date or '').strip()
    if len(d) >= 10 and d[4] == '-' and d[7] == '-':
        d_part = f"{d[2:4]}_{d[5:7]}_{d[8:10]}"
    elif len(d) >= 8 and d[2] == '-' and d[5] == '-':
        d_part = d.replace('-', '_')
    else:
        d_part = d.replace('-', '_').replace('.', '_')[:10] or 'no_date'

    act = (activity or '활동명없음')[:50]

    raw = f"{union}_{branch}_{act}_{d_part}.docx"
    # Drive 안전 문자만 (한글 OK, /:?*<>|" 차단)
    safe = (
        raw.replace(' ', '_')
           .replace('/', '-')
           .replace(':', '-')
           .replace('?', '')
           .replace('*', '')
           .replace('<', '')
           .replace('>', '')
           .replace('|', '-')
           .replace('"', '')
           .replace('\n', '_')
           .replace('\t', '_')
    )
    return safe
