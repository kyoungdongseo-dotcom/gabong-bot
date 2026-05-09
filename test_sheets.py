"""
Google Sheets 연결 진단 스크립트

실행:
  cd ~/gabong-bot
  source venv/bin/activate
  python test_sheets.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

CREDS_FILE = "credentials.json"
PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


# ── 1. 파일 존재 여부 ────────────────────────────────────
section("1. credentials.json 파일 확인")

if not os.path.exists(CREDS_FILE):
    print(f"{FAIL} credentials.json 없음")
    print("  → 서버에서 새 키를 발급한 뒤 다시 업로드하세요.")
    sys.exit(1)

file_size = os.path.getsize(CREDS_FILE)
print(f"{PASS} 파일 존재: {file_size} bytes")

with open(CREDS_FILE, encoding="utf-8") as f:
    try:
        creds_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"{FAIL} JSON 파싱 오류: {e}")
        sys.exit(1)

required_fields = ["type", "project_id", "private_key_id", "private_key",
                   "client_email", "client_id", "token_uri"]
missing = [k for k in required_fields if k not in creds_data]
if missing:
    print(f"{FAIL} 필수 필드 누락: {missing}")
    sys.exit(1)

print(f"  project_id   : {creds_data['project_id']}")
print(f"  client_email : {creds_data['client_email']}")
print(f"  key_id       : {creds_data['private_key_id']}")
print(f"  type         : {creds_data['type']}")
if creds_data['type'] != 'service_account':
    print(f"{FAIL} type이 'service_account'가 아닙니다: {creds_data['type']}")
    sys.exit(1)
print(f"{PASS} 파일 형식 정상")


# ── 2. 설정 값 확인 ────────────────────────────────────
section("2. config.json 설정 확인")

SCOPES = config.get('google_scopes')
SPREADSHEET_ID = config.get('spreadsheet_id')

if not SCOPES:
    print(f"{WARN} google_scopes 미설정 → 기본 스코프 사용")
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
else:
    print(f"{PASS} google_scopes: {SCOPES}")

if not SPREADSHEET_ID:
    print(f"{FAIL} spreadsheet_id 미설정")
    sys.exit(1)
print(f"{PASS} spreadsheet_id: {SPREADSHEET_ID}")


# ── 3. 인증 시도 ────────────────────────────────────────
section("3. Google 서비스 계정 인증")

try:
    from google.oauth2.service_account import Credentials
    import gspread
except ImportError as e:
    print(f"{FAIL} 라이브러리 임포트 실패: {e}")
    print("  → pip install gspread google-auth")
    sys.exit(1)

try:
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    print(f"{PASS} 인증 객체 생성 성공")
except Exception as e:
    print(f"{FAIL} 인증 실패: {e}")
    print()
    err_str = str(e)
    if "invalid_grant" in err_str or "account not found" in err_str:
        print("  원인: 서비스 계정 키가 GCP에서 삭제/비활성화되었습니다.")
        print("  해결: 아래 가이드에 따라 새 키를 발급하세요.")
    elif "invalid_client" in err_str:
        print("  원인: 서비스 계정 자체가 삭제되었거나 프로젝트가 비활성화되었습니다.")
    elif "DECODER routines" in err_str or "private key" in err_str.lower():
        print("  원인: private_key 형식이 손상되었습니다.")
        print("  해결: credentials.json을 재발급하거나 재업로드하세요.")
    sys.exit(1)


# ── 4. 스프레드시트 접근 ────────────────────────────────
section("4. 스프레드시트 읽기 테스트")

try:
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    rows = sheet.get_all_values()
    print(f"{PASS} 접근 성공: 총 {len(rows)}행")
    if rows:
        print(f"  1행 샘플: {rows[0][:4]}")
    if len(rows) >= 9:
        print(f"  5~9행(모니터링 대상): {len(rows[4:9])}행")
except gspread.exceptions.APIError as e:
    print(f"{FAIL} API 오류: {e}")
    if "PERMISSION_DENIED" in str(e):
        print(f"  → 서비스 계정({creds_data['client_email']})에게")
        print(f"    스프레드시트 공유 권한이 없습니다.")
        print(f"    Google Sheets에서 '공유' → 이메일 추가 (뷰어 이상)")
    sys.exit(1)
except Exception as e:
    print(f"{FAIL} 오류: {e}")
    sys.exit(1)


# ── 결과 ────────────────────────────────────────────────
section("결과")
print(f"{PASS} 모든 테스트 통과 — Google Sheets 연동 정상")
