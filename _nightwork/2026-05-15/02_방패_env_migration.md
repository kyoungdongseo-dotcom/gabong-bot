# 방패 (Shield) — telegram_token .env 마이그레이션 설계

작성일: 2026-05-15
작성자: 방패 (Shield)
상태: 설계 (READ-ONLY, 코드 미변경)

---

## 1. Problem statement — 왜 .env 인가

`strategic_plan.md` Section 5 의 **1위 SPOF**: `config.json` 안 `telegram_token` 단일 문자열.

- **노출 위험**: `config.json` 은 `.gitignore` 에 포함되어 있지만, JSON 한 파일이 토큰 + 모든 운영 설정을 동시에 보유 → 백업 공유 / 스크린샷 / 실수 commit 등 1회 사고로 토큰 + 그룹 ID + admin_ids 가 동시 누출.
- **운영 표준 격차**: `.env` + `python-dotenv` 가 이미 main.py L1~2 에 로드되어 있고 (`load_dotenv()` 호출 확인) `.env.example` 에 `TELEGRAM_TOKEN` 샘플까지 작성됨 → 인프라는 갖춰져 있으나 토큰만 분리 안 됨.
- **회전 절차**: BotFather 재발급 후 `.env` 단일 라인 수정 + `systemctl restart` (RTO 3분 목표). 현재 구조에선 `config.json` 의 `telegram_token` 라인을 편집해야 하며 다른 키와 섞여있어 sed 사고 위험.

**목표**: 토큰만 `.env` 로 이동, 그 외 키(group_id, admin_ids, spreadsheet_id, allowed_groups …)는 `config.json` 유지. 1차 마이그레이션 범위 최소화.

---

## 2. Current state inventory — `telegram_token` 참조 전수조사

| 파일 | 라인 | 용도 | 변경 필요 |
|---|---|---|---|
| `main.py` | 93 | `_startup_checks` 필수 키 검증 리스트 | YES (검증 로직 분리) |
| `main.py` | 179 | `ApplicationBuilder().token(...)` — 봇 부팅 핵심 | **YES (최우선)** |
| `config.py` | 41 | `validate_config()` 필수 키 리스트 | YES (검증 분리) |
| `handlers/award_handler.py` | 165 | 사진 다운로드 시 텔레그램 File API URL 구성 | YES |
| `handlers/report_base.py` | 101 | 봉사 사진 다운로드 | YES |
| `handlers/mou_handler.py` | 159 | MOU 사진 다운로드 | YES |
| `handlers/report_docx_handler.py` | 49 | docx 첨부 사진 다운로드 | YES |
| `scripts/test_missing_summary.py` | 98,103,168 | 검증 스크립트 (TELEGRAM_TOKEN env 우선 → config 폴백 이미 구현) | NO (이미 안전) |

총 **5개 운영 파일** + 1개 검증 스크립트(이미 안전).

부수 확인:
- `main.py` L1~2: `from dotenv import load_dotenv` + `load_dotenv()` **이미 존재** → 추가 import 불필요.
- `.env.example` L6: `TELEGRAM_TOKEN=여기에_실제_토큰_입력` **이미 존재** → 템플릿 갱신 불필요.
- `.env` 현재 로컬에 존재 (서버에선 별도 생성 필요).
- 패턴 통일됨: 모든 다운로드 함수가 `config.get('telegram_token')` 한 줄로 호출 → 헬퍼 함수 도입 또는 `os.environ` 직접 호출 모두 가능.

---

## 3. .env template (서버에 생성할 파일)

**파일 경로**: `~/gabong-bot/.env` (Oracle Cloud 서버)

```dotenv
# 가봉봇 운영 환경변수 (서버 전용)
# 이 파일은 .gitignore 에 등록되어 GitHub 에 올라가지 않습니다.
# 절대 공유 / 백업 / 스크린샷 금지.

# [필수] 텔레그램 봇 토큰 (BotFather 발급)
TELEGRAM_TOKEN=[REDACTED - revoked via BotFather 2026-05-16]

# [선택] 다른 키들은 config.json 유지 — 마이그레이션 범위 외
```

권한: `chmod 600 .env` (소유자만 read/write).

---

## 4. .gitignore 확인

```
# 환경변수 (시크릿 포함)
.env
.env.local
.env.*.local
```

✅ 이미 `.env` 가 `.gitignore` 에 등록됨 → 추가 작업 없음.

추가 확인 사항: `git ls-files | grep -E '^\.env$'` 가 empty 인지 서버에서 검증 (혹시 과거에 실수 commit 된 흔적이 없는지).

---

## 5. Per-file code changes (before / after)

### 5.1 `config.py` — 신규 헬퍼 추가

토큰을 가져오는 단일 진입점을 만들어 `os.environ` 우선 + `config.json` 폴백.

**추가 (파일 끝에 append)**:
```python
def get_telegram_token():
    """텔레그램 봇 토큰 조회 — .env 우선, config.json 폴백.

    마이그레이션 기간 동안 backward compatibility 유지.
    Post-migration (Section 9) 에서 config.json 폴백 제거 예정.
    """
    return os.environ.get('TELEGRAM_TOKEN') or get('telegram_token')
```

**`validate_config()` 수정 (L41)**:
```python
# before
required_keys = ['telegram_token', 'group_id', 'admin_ids']

# after
required_keys = ['group_id', 'admin_ids']  # telegram_token 은 .env 로 이동
# 토큰 별도 검증
if not get_telegram_token():
    print("필수: TELEGRAM_TOKEN (.env) 또는 telegram_token (config.json) 미설정")
    return False
```

### 5.2 `main.py` L179 — 봇 부팅 토큰

```python
# before
.token(config.get("telegram_token"))

# after
.token(config.get_telegram_token())
```

### 5.3 `main.py` L93 — startup check

```python
# before
required_keys = ["telegram_token", "group_id", "admin_ids", "spreadsheet_id"]
for key in required_keys:
    if not config.get(key):
        print(f"⚠️ [진단] config.json 필수 키 누락: {key}")
        ok = False

# after
required_keys = ["group_id", "admin_ids", "spreadsheet_id"]
for key in required_keys:
    if not config.get(key):
        print(f"⚠️ [진단] config.json 필수 키 누락: {key}")
        ok = False
if not config.get_telegram_token():
    print("⚠️ [진단] TELEGRAM_TOKEN (.env) 또는 telegram_token (config.json) 미설정")
    ok = False
```

### 5.4 `handlers/award_handler.py` L165

```python
# before
token = config.get('telegram_token')

# after
token = config.get_telegram_token()
```

### 5.5 `handlers/report_base.py` L101

```python
# before
token = config.get('telegram_token')

# after
token = config.get_telegram_token()
```

### 5.6 `handlers/mou_handler.py` L159

```python
# before
token = config.get('telegram_token')

# after
token = config.get_telegram_token()
```

### 5.7 `handlers/report_docx_handler.py` L49

```python
# before
token = config.get('telegram_token')

# after
token = config.get_telegram_token()
```

**변경 규모**: 7 라인 수정 + `config.py` 에 신규 함수 5~7라인 추가. 총 약 12~15 라인.

---

## 6. Deployment order — 단계별 실행

각 단계마다 verify 확인 후 다음 단계 진행.

### Phase A: 서버 사전 준비 (다운타임 없음)

1. **서버 SSH 접속 → `.env` 파일 생성**
   ```bash
   cd ~/gabong-bot
   nano .env
   # TELEGRAM_TOKEN=<config.json 의 telegram_token 값 복사>
   chmod 600 .env
   ```
   → verify: `cat .env | grep TELEGRAM_TOKEN` 출력 확인 + 권한 `-rw-------`.

2. **`.env` git 추적 안 되는지 확인**
   ```bash
   git status | grep -E '\.env$'   # 출력 없어야 정상
   git ls-files | grep -E '^\.env$' # 출력 없어야 정상
   ```

### Phase B: 코드 배포 (backward-compatible)

3. **로컬에서 Section 5 변경 적용 → 커밋 → push**
   - `config.py` 헬퍼 추가
   - `main.py` 2곳 + 4개 핸들러 수정
   - 키 포인트: `get_telegram_token()` 은 폴백 포함 → `.env` 없어도 기존 `config.json` 으로 동작 (rollout 안전망).

4. **서버 pull + restart**
   ```bash
   cd ~/gabong-bot
   git pull origin main
   find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
   sudo systemctl restart gabong-bot.service
   sleep 5
   sudo journalctl -u gabong-bot.service --no-pager -n 50
   ```
   → verify: "봇 시작!" 로그 + `[진단] 모든 환경 점검 통과` + 텔레그램으로 `/status` 응답 확인.

### Phase C: 출처 검증 (token 출처 .env 인지 확인)

5. **임시 검증**: 서버에서 `config.json` 의 `telegram_token` 라인을 잘못된 값으로 1자만 바꿔서 (예: 끝에 `_INVALID` 추가) restart → 봇이 정상 작동하면 `.env` 에서 읽고 있음. 검증 후 즉시 원복.
   - 더 안전한 대안: Section 8 참조 (`scripts/test_missing_summary.py` 가 이미 출처 표시 로그 제공).

### Phase D: config.json 토큰 제거 (Section 9 — 1~2주 안정화 후)

6. 안정 운영 1주 확인 후 `config.json` 의 `telegram_token` 키 자체를 제거. 폴백 코드도 제거 (Section 9 참조).

---

## 7. Rollback plan

**Phase B 이후 봇 부팅 실패 시**:
1. 즉시: `git revert <commit-hash>` → push → 서버 pull → restart. (코드 한 단위로 revert 가능)
2. 또는: `.env` 의 `TELEGRAM_TOKEN` 라인이 정확한지 확인 (BotFather 토큰 복붙 시 공백/줄바꿈 사고 빈번).
3. `config.json` 의 `telegram_token` 은 Phase D 전까지 그대로 두므로, 폴백 경로가 살아있음 → `.env` 만 일시 삭제하면 즉시 원복.

**Rollback 안전 핵심**: Phase B 의 변경은 backward-compatible (`os.environ.get() or config.get()`). `.env` 없어도 `config.json` 로 부팅 가능 → 실질적 0-risk.

**Phase D 이후 사고**: `git revert` 로 폴백 복원 + `config.json` 에 `telegram_token` 재기입 후 restart.

---

## 8. Verification — 토큰 출처 확인

### 8.1 기존 스크립트 활용
`scripts/test_missing_summary.py` 의 L98~116 에 이미 출처 진단 로직 존재:
- L103: `config.json` 의 `telegram_token` 키 탐색
- L116: `TELEGRAM_TOKEN`, `BOT_TOKEN`, `TELEGRAM_BOT_TOKEN` 환경변수 탐색
- L168: 안내 메시지 "확인: .env 의 TELEGRAM_TOKEN 또는 config.json 의 telegram_token"

→ 서버에서 `python3 scripts/test_missing_summary.py` 실행 시 어느 쪽이 잡히는지 출력됨.

### 8.2 1회용 진단 (배포 직후)
서버 `~/gabong-bot` 에서:
```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
env_token = os.environ.get('TELEGRAM_TOKEN')
import json
cfg = json.load(open('config.json'))
cfg_token = cfg.get('telegram_token')
print(f'env  TELEGRAM_TOKEN: {\"SET (\" + env_token[:10] + \"...)\" if env_token else \"NOT SET\"}')
print(f'cfg  telegram_token: {\"SET (\" + cfg_token[:10] + \"...)\" if cfg_token else \"NOT SET\"}')
print(f'우선순위: env 우선 → 실제 사용 출처: {\"env\" if env_token else \"config.json\"}')"
```

### 8.3 기능 smoke test
- `/status` 명령 (관리자) → 응답 확인
- 텍스트 보고서 1건 테스트 그룹에서 전송 → Word 생성 + 사진 다운로드 정상 (사진 다운로드는 token 사용)

---

## 9. Post-migration — `config.json["telegram_token"]` 제거 시점

### 제거 조건 (AND)
- [ ] Phase B 배포 후 **7일 이상** 무중단 운영
- [ ] Section 8.2 진단으로 **실제 사용 출처가 env** 확인
- [ ] 봇 재시작 1회 이상 + 사진 보고서 정상 처리 1건 이상

### 제거 작업
1. `config.py` 의 `get_telegram_token()` 에서 폴백 제거:
   ```python
   # before
   return os.environ.get('TELEGRAM_TOKEN') or get('telegram_token')

   # after
   token = os.environ.get('TELEGRAM_TOKEN')
   if not token:
       raise RuntimeError("TELEGRAM_TOKEN 환경변수 미설정 (.env 확인)")
   return token
   ```
2. 서버 `config.json` 에서 `"telegram_token": "..."` 라인 삭제 + 봇 restart.
3. 검증: `python3 -c "import config; print(config.load_config().get('telegram_token'))"` → `None` 출력.

### 영구 작업 (선택)
- `scripts/test_missing_summary.py` L103 의 `config.json` 토큰 폴백 로직 제거 → env 단일 경로.
- `_planning/strategic_plan.md` Section 5 의 1위 SPOF 항목을 "mitigated" 로 갱신.

---

## 부록 — 추가 발견 / 다음 작업 추천

### 작업 중 발견
- `config.get()` 패턴이 캐시 없는 매 호출 디스크 read (`config.py` L28~31). 사진 1장당 `config.get('telegram_token')` 1회 호출되므로 보고서 10장 album = 디스크 10회. 마이그레이션 후엔 `os.environ` 으로 in-process 조회로 바뀌어 **부수적 성능 개선** 발생.
- `config.get_cached()` 함수가 별도로 존재 (L52~57) 하지만 토큰 다운로드 4곳에서 사용 안 함 → 일관성 결함. 마이그레이션이 이 결함도 해소.
- `.env` 파일이 로컬 (macOS) 에 이미 실제 토큰 보유 (L4 확인). 서버 `.env` 도 동일 값인지 확인 필요 — 운영 환경 일관성 검토.

### 다음 작업 추천 (우선순위)
1. **본 마이그레이션 실행** (12~15 LoC, 2시간, Risk Low) — 본 문서대로 진행.
2. **`config.json` 일일 백업에 포함** (`run_backup` 에 3 LoC, Risk Low) — strategic_plan Section 5 #4. 토큰 .env 이동 후에도 admin_ids/allowed_groups 손실 위험은 그대로.
3. **`REPORT_GROUP_ID` 하드코딩 → config 이동** (2위 SPOF, ~50 LoC) — 4곳 (`message_handler.py:13` 등) 수정.

### 인사이트
- 이번 작업은 **infrastructure 정비형 변경** — 사용자 가시 기능 0% 변경, 운영 안전성 ↑. 6월 정상 운영 대비 진척에는 영향 없으나 **사고 대응 RTO 가 분 단위로 단축**됨 (토큰 회전 시).
- backward-compatible 폴백 패턴은 **모든 secret 마이그레이션의 표준** — 향후 `ANTHROPIC_API_KEY`, Google service account 등도 동일 패턴 적용 가능.

### 사용자 결정 필요
- (A) 본 설계대로 진행 (단일 헬퍼 `config.get_telegram_token()` 추가) ← 권장
- (B) 헬퍼 없이 각 호출 지점에서 `os.environ.get('TELEGRAM_TOKEN') or config.get('telegram_token')` 인라인 → 핸들러 7곳 모두 동일 라인 중복. 비권장.
- (C) 본 작업 보류, strategic_plan Section 1 #1 (미제출 지파 알림) 먼저 진행 — Closing 권장사항대로.
