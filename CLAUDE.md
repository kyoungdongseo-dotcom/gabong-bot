# GAbongAI Bot - 작업 표준

## ⭐ 작업 원칙 (모든 작업에 필수 적용)

### 1. Think Before Coding
- 가정을 명확히 표현, 불확실하면 질문
- 여러 해석 가능하면 모두 제시 (silent 결정 금지)
- 단순한 접근법 있으면 먼저 제안
- 불명확하면 멈추고 사용자에게 질문

### 2. Simplicity First
- 요청한 것만 최소 코드로 구현
- 추측성 기능/유연성 추가 금지
- 200줄 가능하면 50줄로 재작성
- "이것도 좋겠다" 자제

### 3. Surgical Changes
- 필요한 것만 변경
- 인접 코드 "개선" 안 함 (요청 없으면)
- 기존 스타일 매치
- 모든 변경 = 사용자 요청 직결
- 죽은 코드 발견하면 언급만, 삭제 X

### 4. Goal-Driven Execution
- 검증 가능한 목표 설정
- 단계별 계획 명시:
  1. [Step] → verify: [check]
  2. [Step] → verify: [check]
- 각 단계 검증 후 다음 진행

## 📋 Claude Code 명령 형식 (필수)

모든 작업 명령에 포함:
1. 배경 (왜 이 작업?)
2. 작업 (정확한 변경 사항)
3. 검증 (어떻게 확인?)
4. 주의사항 (sed 사용, 부분 편집, 전체 재작성 금지)
5. 양방향 피드백 (작업 후 보고):
   - 분석/구현 중 추가 발견
   - 다음 작업 추천
   - 인사이트
   - 사용자 결정 필요 사항

## 🎯 프로젝트 정보

- **프로젝트**: GAbongAI Bot (텔레그램 봇)
- **배포**: Oracle Cloud Always Free
- **언어**: Python 3.10
- **DB**: SQLite (`gabong.db`, `bot_data.db`)
- **목적**: 13개 지파 보고서 자동화 + 조직 운영 효율화

## 🔄 양방향 피드백 (절대 빼먹지 말 것)

모든 작업 완료 시 다음을 반드시 보고:

### 1. 작업하면서 발견한 추가 개선점
- 코드 품질 (중복, 복잡도, 가독성)
- 데이터 흐름 (병목, 누락, 비효율)
- 사용자 경험 (UX, 안내 부족, 혼란)
- 향후 확장성 (구조적 한계, 결합도)

### 2. 부수적으로 발견한 문제
- Dead code (미사용 함수/import)
- 보안 이슈 (권한, 노출, 인젝션)
- 성능 병목 (느린 쿼리, 메모리 누수)
- 향후 위험 (이슈 가능성)

### 3. 다음 작업 추천 (우선순위 순)
- 1순위, 2순위, 3순위 명시
- 각 작업량 (라인 수, 시간)
- 위험도 (Low/Med/High)
- ROI (투자 대비 효과)

### 4. 알면 좋을 인사이트
- 작업 중 깨달은 것
- 패턴 발견
- 함정/주의점
- 데이터 기반 발견

### 5. 6월 정상 운영 대비 진척 상황
- 영역별 진척도 (%)
- 변동 사항 (이전 대비)
- 6월 운영 가능 여부 평가

## 📋 작업 워크플로우

### 1단계: 분석 (코드 수정 X)

새 작업 시작 전:
- 현재 코드 구조 파악
- 영향 받는 파일 확인
- 위험 요소 식별
- 대안 검토
- 사용자 결정 필요 사항 정리

### 2단계: 사용자 결정 대기

- 옵션 제시 (각 장단점 포함)
- 권장 사항 명시
- 사용자가 선택하면 진행

### 3단계: 구현

- sed/부분 편집만 사용
- **전체 재작성 절대 금지**
- import, load_dotenv, config 로드 부분 보존
- 기존 정상 케이스 깨지지 않게

### 4단계: 검증

- `py_compile` 모든 수정 파일
- 단위 테스트 (가능한 경우)
- 시나리오별 검증

### 5단계: 배포 + 보고

- git push
- 서버 배포 명령어 정리
- 양방향 피드백 (위 5가지 항목)

## 🚫 절대 금지

1. **전체 파일 재작성** (`cat > file.py`)
   - 항상 sed/str_replace/부분 편집만 사용
   - import 누락 위험

2. **분석 없는 즉시 코드 수정**
   - 사용자 결정 필요 사항 먼저 확인

3. **양방향 피드백 생략**
   - 모든 작업 완료 후 필수
   - 작은 작업이라도 인사이트 보고

4. **검증 없는 git push**
   - py_compile 통과 후에만 push

## ✅ 항상 적용

1. **데이터 일관성 우선**
   - Word 정상 → 시트 저장 (트랜잭션 패턴)
   - 데이터 손실 위험 차단

2. **사용자 경험 친절**
   - 안내형 톤 (지시형 X)
   - 명확한 다음 행동 안내

3. **에러 처리 견고**
   - try/except 적극 사용
   - 자동 재시도 (사진/시트/DM)
   - 관리자 백업 알림

4. **백업 가능성 유지**
   - 주요 변경 전 git commit
   - DB 스키마 변경 시 마이그레이션 안전 (`PRAGMA table_info` 사전 체크)

## 🎯 핵심 시스템 구조

### 보고서 시스템 (3종)
- 봉사보고서: `handlers/message_handler.py`
- MOU 보고서: `handlers/mou_handler.py`
- 수상보고서: `handlers/award_handler.py`
- 공통 베이스: `handlers/report_base.py`
- 파싱 유틸: `handlers/report_parser_utils.py`

### 트랜잭션 패턴 (필수 준수)
1. 사진 다운로드 (D-1 엄격: 1장 실패 시 차단)
2. Word 파일 생성
3. ✅ 검증 통과 → 시트 저장 (재시도 3회)
4. 서무 DM 전송
5. 보고자 reply

### 단계별 추적 (8단계)
- received → parsed → sheet_saved → photos_downloaded
- → docx_generated → recipient_dm_sent → reporter_ack_sent → finalize
- 모든 단계 `report_log` 테이블에 기록

### dedup 정책
- 10분 윈도우 (`window_sec=600`)
- 같은 사람: 강 경고
- 다른 사람: 약 경고
- 강제 진행 + 경고 (옵션 3)
- hash 정규화 (공백/대소문자)
- hash 식:
  - 봉사: `지파|교회|활동명|활동일시[:10]`
  - MOU: `지부|협약명|기관명`
  - 수상: `지부|수상명|수상자`

### PENDING 키 (동시 제출 분리)
- `(chat_id, topic_id, user_id)` 3-tuple
- DB 영속화 (`pending_reports`, `pending_photos`)
- 봇 재시작 시 자동 복원

### 사진 누적 정책
- 최대 10장 (`MAX_PHOTOS = 10`)
- TTL 10분 (여러 앨범 누적 시간)
- 11장째부터 silent drop + 보고자 안내

## 🔧 주요 기술 스택

- python-telegram-bot
- python-docx (Word 생성)
- gspread + google-api-python-client (스프레드시트)
- APScheduler (스케줄)
- SQLite (DB)
- pytz (KST 시간대)
- requests (텔레그램 file 다운로드)

## 📊 데이터 보관 정책

| 데이터 | 보관 기간 | 정리 시점 |
|---|---|---|
| `recent_submissions` | 24시간 | 매일 03:30 |
| `report_log` | 90일 | 매주 일요일 04:00 |
| `/tmp/*.docx` | 24시간 | 매주 일요일 04:30 |
| 백업 zip | 7일 (텔레그램 DM) | 매일 03:00 |
| `format_help_sent` | 무한 | UNIQUE 제약 — cleanup 불필요 |
| `pending_reports/photos` | 10분/5분 TTL | restore 시 자동 필터 |

## 📝 사용자 정보

- 메인 관리자: `97057565` (gamdongwon)
- 서무 (보고서 수신): `754270008`
- 관리자 6명: `admin_ids` 리스트 (config.json)
- 총 13개 지파 운영
- 보고서 그룹: `-1002777848839`
  - 수상 토픽: `3553`
  - MOU 토픽: `3225`
  - 봉사 토픽: 미지정 (그룹 전체)

## 🚀 다음 작업 후보 (우선순위)

1. **진행 상황 실시간 표시** (300줄, edit_message_text 패턴)
2. **날짜 정규화** (50줄, dateutil.parser)
3. **`/status`에 dedup 통계 추가** (20줄)
4. **미제출 지파 자동 알림** (운영 정책 결정 후)
5. **WAL 모드 적용** (동시성 개선)
6. **활동계기 항목 추가** (사용자 제안)

## ⚙️ 운영 명령어

### 서버 배포 (표준 패턴)
```bash
cd ~/gabong-bot
git pull origin main

# .pyc 캐시 정리 (코드 변경 후 권장)
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

sudo systemctl restart gabong-bot.service
sleep 5

# 부팅 확인
sudo journalctl -u gabong-bot.service --no-pager -n 30 | grep -E "DB 초기화|복원|등록 완료|error"
```

### 봇 명령어
- `/help` — 보고서 형식 안내 (인라인 버튼)
- `/myreports` — 본인 제출 이력 30일
- `/report_stats` — 월간 통계 (관리자만)
- `/status` — 봇 상태 (관리자만)
- `/backup` — 즉시 DB 백업 (관리자만)
- `/schedule`, `/report`, `/monthly` — 분석 명령어

### DB 직접 조회
```bash
sqlite3 ~/gabong-bot/data/gabong.db ".tables"
sqlite3 ~/gabong-bot/data/gabong.db "SELECT * FROM report_log ORDER BY id DESC LIMIT 10"
```

## 🛠️ 환경 특이사항

- **`utils.py` 와 `utils/` 동시 존재 금지**: 패키지(`utils/__init__.py`)만 사용. `utils.py`는 dead code로 제거됨.
- **`utils/permissions.py`** 별도 모듈 → utils 가 패키지여야만 import 가능
- **이중 DB**: `gabong.db` (reminders + 보고서 + log) / `bot_data.db` (messages + chat_modes)
  - `init_database()` 호출 시 양쪽 모두 초기화됨 (utils → database.init_db 자동 호출 + main.py 명시 호출)

## 🔒 보안 / 권한

- 관리자 전용 명령어: `admin_ids` 체크
- 그룹 화이트리스트: `allowed_groups`
- 신규 그룹 차단: `join_guard` 플러그인
- 토큰 노출 금지: `config.json`은 `.gitignore`
- `serviceAccountKey.json` 권한 600 권장

## 🔐 권한 매트릭스

`admin_ids` (6명): 97057565(메인), 754270008(서무), 414481241, 5242761926, 1104086017, 1062746453

### 📊 리포트/점검 (admin_ids 6명)
- `/weekly_ops` — 주간 운영 리포트
- `/report_stats` — 월간 통계
- `/status` — 봇 상태
- `/backup` — 즉시 백업
- `/admin` — 관리자 대시보드
- `/schedule`, `/weekly_report` — 일정/주간 리포트
- `/reminder_stats`, `/reminder_analysis`

### 📢 일반 관리 (admin_ids 6명)
- `/report`, `/monthly` — 보고서 분석
- `/notice` — 총회봉교부 단일 토픽 공지 ✅ 안전
- `/broadcast` — 13개 그룹 일괄 공지 ✅ 안전
- `/sheet` — 시트 데이터 → 그룹 발송 ✅ 안전 (admin 6명)
- `/add_group` — 신규 그룹 화이트리스트 추가 ✅

### 🎯 메인 관리자 전용 (my_user_id 1명)
- `/reply` — 마지막 멘션 답변 ✅ 매우 안전 (97057565만)
  LAST_MENTION 이 my_user_id 키 단일 → 다른 admin 호출해도 동작 안 함

### 🤖 AI 호출 (admin_ids 6명) — **모든 진입점**
- `/ai`, `/summary`, `/reset` — `check_admin` (utils.permissions)
- `/mode`, `/summary_detailed`, `/summary_brief` (ai_advanced)
- `@봇이름` 멘션 — admin_ids 체크 (트래픽/비용 통제)
- "요약" 키워드 자동 호출 — 봇 멘션 분기 안에서 admin 체크 통과 후 동작

### ⏰ 리마인더 (admin_ids 6명)
- `/remind_daily`, `/remind_weekly`, `/remind_biweekly`, `/remind_monthly`
- `/broadcast_remind_*` — 13개 그룹 일괄
- `/my_reminders`, `/delete_reminder`

**리마인더 시스템 정상화 (2026-05-11 Phase 1)**:
- 등록한 그룹/토픽으로 정확히 발송됨 (`send_reminder` 수정)
- DB 컬럼: `group_id`, `topic_id`, `user_id` 모두 저장
- 봇 재시작 시 topic_id 함께 복원
- broadcast_remind_* 는 13개 그룹 일괄 발송 (변경 없음)
- 발송 로그: `📩 리마인더 발송: chat=N topic=N`
- Phase 2 (일반 사용자 확장) 인프라 준비됨 (1주 안정화 후 결정)

### 👥 일반 사용자 (누구나)
- `/help` — 도움말 (인라인 버튼)
- `/myreports` — 본인 제출 이력 30일
- `/start` — 봇 시작 (notice_plugin, ⚠️ 별도 분석 필요)

### 🔍 자동 알림 (사용자 액션)
- `mention_keywords` 자동 알림 (16개 키워드)
  → 총회봉교부 토픽 알림. 발송 가능 그룹 14개 (allowed - exclude).
  → ✅ **다층 보호**: admin 제외 + EXCLUDE_GROUPS 13개 + partial_exclude
  → ✅ **빈도 제한 적용**: 사용자별 1시간 3회 (텔레그램 20msg/분 한도 보호)
  → 한도 초과 시 silent drop + 로그 (`⚠️ mention_keyword 빈도 제한 차단`)
  → 정상 트리거 시 `📣 mention 트리거` 로그
- `my_keywords` 메인 관리자 DM 알림 (5개 키워드: `@gamdongwon`, `부장님`, `부장`, `봉교부장님`, `봉사교통부장님`)
  → ✅ **빈도 제한 적용**: 사용자별 1시간 3회 (메모리 dict, 봇 재시작 시 초기화)
  → 한도 초과 시 silent drop + 로그 (`⚠️ my_keyword 빈도 제한 차단`)
  → 정상 트리거 시 `📣 my_keyword 트리거` 로그

### 📊 보고서 처리 이력 (`report_log`)

- `log_report_stage()` 가 모든 보고서 처리 단계 기록
- `get_user_reports()` 는 보고서별 outcome 판정 → `/myreports`
- **outcome 판정 시 `(user_id, report_type, message_id)` 3개 조합으로 매칭** 필수
  - `message_id` 필터 누락 시: 같은 user 의 다른 보고서 stage 가 섞임
  - 1건의 fail 이 동일 user 의 직후 보고서들도 fail 로 잘못 판정 (2026-05-11 버그 수정)
- DB 스키마에 `message_id` 컬럼 있음 → SQL 작성 시 항상 포함

### 📅 /schedule 봉사 일정 (2026-05-11 다중 블록 지원)
- 봉사달력 시트는 **주별 블록** 구조 (5월부터):
  - 행 18 = 1주차 날짜 (3, 4, 5, 6, 7, 8, 9)
  - 행 19~30 = 1주차 봉사 내용
  - 행 39 = 2주차 날짜 (10~16), 행 40~ = 2주차 봉사
  - 3주차, 4주차, 5주차 동일 패턴
- `is_date_header()`: **7개 모두** 1~31 정수면 헤더로 판정 (봉사달력 7일 기준, 2026-05-11 임계값 강화)
  - 임계값 7로 false-positive 완전 차단 — 봉사 내용 행에 숫자 있어도 오인 X
  - 미래 시트 구조 변경 시에도 안전 (7일 가정 유지되는 한)
- `find_week_blocks()`: 헤더부터 다음 헤더 직전까지를 블록으로 그룹화
- `parse_schedule_from_rows()`: 모든 블록 스캔 → `this_week_range()` 으로 필터링
- 매월 새 시트 자동 처리 (구조 동일 가정) — 6월/7월/... 자동 작동
- 변경 시 `print("[/schedule] 발견 블록 수: N")` 로그로 검증

### 📋 스프레드시트 변경 감지
- `utils.check_changes` — 60초 폴링, 행 5~9 모니터링
- **디바운싱 30분**: 같은 행 알림 후 30분 내 추가 변경 silent skip
- 다른 행은 독립 카운트 (각자 첫 변경 즉시 알림)
- 메모리 dict (`LAST_SHEET_NOTIFY`, 봇 재시작 시 초기화)
- 로그: `📋 sheet 변경 감지 → 알림` / `⏸️ sheet 알림 디바운싱`

### 📋 봉사보고서 received/parsed 기록 (2026-05-12 보강)
- **3개 finalize 직행 경로 모두 received + parsed 기록 보장**:
  1. handle_all_messages (텍스트만 또는 텍스트+사진): line 522 (기존)
  2. process_media_group caption 분기 (사진 album + caption): line 360 (신규)
  3. handle_photo_messages 케이스 B (단일 사진 + caption): line 455 (신규)
- **누락 시 영향**: /myreports 에서 0건 표시, 통계 왜곡
- 호출 패턴 통일: `log_report_stage('service', 'received', 'ok', user_id=, chat_id=, topic_id=, message_id=, detail=)` + `parsed`

### 🔐 권한별 기능 매트릭스 (2026-05-13 정리)

**권한 4단계:**

| 레벨 | 권한 | 인원 | 정의 위치 |
|---|---|---|---|
| Lv 0 | 외부 사용자 | — | 봇과 1:1 DM 가능 |
| Lv 1 | 허용 그룹 멤버 | — | allowed_groups 27개 |
| Lv 2 | 관리자 | 6명 | config.admin_ids |
| Lv 3 | 메인 관리자 | 1명 (97057565) | config.my_user_id |

**일반 사용자 명령어 (5개, 본인 데이터만):**
- `/start` — 봇 안내
- `/help` — 보고서 양식 안내 (인라인 버튼)
- `/myreports` — 본인 보고서 이력 30일
- `/reminder_stats` — 본인 리마인더 통계
- `/reminder_analysis` — 본인 리마인더 분석

**관리자 명령어 (33개) — 점검(8) / 공지(5) / AI(8) / 리마인더(10) / 그룹관리(2)**

**메인 관리자 전용 (3개)**: `/reply`, `/admin`, 이모지 반응 forward

**자동 기능 (그룹 내, 권한 체크 없이):**
- 봉사보고서 자동 처리 (REPORT_GROUP_ID 토픽 필터)
- MOU/수상 자동 처리 (토픽 3225/3553)
- 멘션 키워드 알림 (exclude_groups 제외 + rate limit 1h 3회)
- 리마인더 키워드 트리거
- 메시지 로깅 (AI 컨텍스트)

**그룹별 차단/허용:**

| 그룹 분류 | 멘션 | 반응 | AI | 보고서 | 리마인더 | broadcast |
|---|---|---|---|---|---|---|
| 메인 그룹 | ❌ | ❌ | ✅ | ❌ | ✅ | (수신) |
| REPORT 그룹 | ❌ | ✅(main만) | ✅ | ✅ | ✅ | ❌ |
| 13개 지파 | (개별) | ✅ | ✅ | ❌ | ✅ | ✅ 수신 |
| 부분 차단 (-1003689540938) | 일부 키워드 | ✅ | ✅ | ❌ | ✅ | ❌ |
| allowed 외 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**권한 체크 헬퍼 (utils/permissions.py, 2026-05-13 강화):**

```python
is_admin(user_id)              # bool 동기
is_main_admin(user_id)         # bool 동기
await check_admin(update, ctx)         # silent True/False
await require_admin(update, ctx)       # 거부 메시지 + False
await require_main_admin(update, ctx)  # 거부 메시지 + False
```

→ **새 핸들러 작성 시**: `require_admin` (거부 메시지 보냄) 또는 `check_admin` (silent) 사용 권장.
→ **기존 4가지 패턴 (인라인 16곳 + ADMIN_IDS 상수 7곳 + check_admin 7곳 + my_user_id 다수) 점진 마이그레이션 후보**.

### 🗂️ 그룹 관리 매트릭스 (2026-05-13 정리)

**config.json 그룹 설정 8종:**

| 설정 키 | 의미 | 개수 | 추가 시점 |
|---|---|---|---|
| `group_id` (단일) | 메인 그룹 ID | 1 | 봇 셋업 시 고정 |
| `topic_id` (단일) | 메인 그룹 알림 토픽 | 1 | 봇 셋업 시 고정 |
| `allowed_groups` | 봇 운영 허용 그룹 (마스터) | 27 | 새 지파/그룹 추가 시 |
| `exclude_groups` | 멘션 알림 차단 그룹 | 13 | 자기 그룹 → 자기 알림 방지 |
| `reaction_exclude_groups` | 이모지 반응 차단 그룹 | 1 | 메인 그룹만 일반적 |
| `broadcast_groups` | /broadcast 발송 대상 | 13 | 13개 지파 그룹 |
| `summary_groups` | 일일 요약 대상 | 1 | 보통 메인 그룹만 |
| `partial_exclude_groups` | 특정 키워드만 차단 | 1 dict | 그룹별 세부 정책 |

**기능별 차단/허용 매트릭스:**

| 기능 | 적용 범위 | 사용 위치 |
|---|---|---|
| 봉사보고서 자동 처리 | `REPORT_GROUP_ID` 하드코딩 | `message_handler.py:13` (-1002777848839) |
| 멘션 키워드 알림 | exclude_groups 제외 | `message_handler.py:586` |
| 이모티콘 반응 | reaction_exclude_groups 제외 | `reaction_handler.py:15` |
| AI 명령 (/ai, /summary) | allowed_groups 만 | `ai_handler.py:13-14` |
| /notice | 메인 그룹 고정 | `notice_handler.py:75-76` |
| /broadcast | broadcast_groups | `notice_handler.py:100` |
| 리마인더 (개별) | 호출한 그룹 | `reminder_handler.py:22-23` |
| 일일 요약 | summary_groups | `utils:send_daily_summary` |
| /schedule, /myreports | 권한만 (그룹 무관) | 다양 |
| 일반 텍스트 로그 | 차단 X | `log_message` |

**새 그룹 추가 체크리스트:**
- [ ] `allowed_groups` 에 추가 (봇 운영하려면 **필수**)
- [ ] `exclude_groups` 에 추가? (멘션 자기참조 방지)
- [ ] `reaction_exclude_groups` 에 추가? (이모지 차단 필요?)
- [ ] `broadcast_groups` 에 추가? (공지 받을 그룹?)
- [ ] `summary_groups` 에 추가? (일일 요약 대상?)
- [ ] `partial_exclude_groups` 에 추가? (특정 키워드만 차단?)

**정책 원칙:**
1. `allowed_groups` 가 마스터 — 모든 다른 그룹은 여기 포함
2. `exclude_groups` 는 부분 제거 — allowed 중에서 멘션만 차단
3. `broadcast_groups` 는 별도 — allowed 무관 (현재 13개 모두 allowed 안에)
4. `REPORT_GROUP_ID` 하드코딩 중 — 미래 config 이동 후보

**일관성 검증 명령:**
```bash
python3 -c "
import json
d = json.load(open('config.json'))
allowed = set(d.get('allowed_groups', []))
exclude = set(d.get('exclude_groups', []))
broadcast = set(g['id'] for g in d.get('broadcast_groups', []))
print(f'멘션 받는 그룹: {len(allowed - exclude)}개')
print(f'broadcast 중 allowed 없음: {broadcast - allowed}')
"
```

### ⏰ 리마인더 자동 비활성화 (2026-05-13 추가)
- `send_reminder` 발송 실패 시 패턴별 처리 (`utils/__init__.py`):
  - `Forbidden` (봇 추방): **즉시 is_active=0** + admin DM
  - `BadRequest` (토픽 삭제, chat not found): 즉시 비활성화
  - 일반 `Exception` (네트워크): `REMINDER_FAIL_COUNT` 누적, **3회 시 비활성화**
- `_deactivate_reminder()`: DB UPDATE → scheduler.remove_job → admin 알림 (best-effort)
- 카운터는 메모리 (`REMINDER_FAIL_COUNT`) — 봇 재시작 시 리셋
- **silent fail 시리즈 8번째 사례 해소**: 추방된 그룹의 리마인더 무한 누적 차단

### 📝 parse_report 매칭 정책 (2026-05-12 추가)
- 키워드 매칭: 정규식 `r'(활동|봉사)\s*보고'`
  - "활동보고", "봉사보고" — 기존
  - "활동 보고", "봉사 보고", "봉사 활동 보고" — 신규 (띄어쓰기 허용)
- **Why**: 자연스러운 한국어 띄어쓰기로 인한 silent fail 방지
- **유사 위험 영역** (양식 매칭 너무 엄격):
  - `handlers/award_handler.py`: `'수상' in caption and '보고' in caption` — 띄어쓰기 OK 지만 다른 패턴 부분
  - `handlers/mou_handler.py:84`: 키워드 리스트 — 명시적 처리

### 🎞️ album / media_group 처리 표준 (2026-05-12 추가)
- `ALBUM_WAIT_SECONDS = 7` (handlers/message_handler.py 상단)
  - 텔레그램 album 평균 도착 시간 마진
  - 3초 였을 때 caption=NO 오판정 빈발 → 7초 안전 마진
  - 변경 시 운영 모니터링 필수
- caption 늦게 도착 가능성 인지 → **다층 안전망**:
  1. 1차: 7초 sleep 으로 대부분 잡음
  2. 2차: PENDING_PHOTOS 저장 + "사진만 접수" 안내 (어제 추가)
  3. 3차 (필요 시 미래 작업): caption 도착 시 재처리
- 측정 가능한 로그:
  - `📸 album[봉사]: photos=N caption=YES/NO` — 비율 모니터링
  - `📸 사진 N장 접수 — 보고서 형식 텍스트도` — 안전망 효과 측정
- **동일 패턴**: `handlers/mou_handler.py:612`, `handlers/award_handler.py:636` 도 `sleep(3)` 사용 — 일관성 검토 후보

### 📸 사진 처리 (2026-05-12 업데이트)
- caption 없는 album 도 `PENDING_PHOTOS` 에 저장 (TTL 600초)
- 사용자에게 "📸 사진 N장 접수 — 보고서 형식 텍스트도 보내주세요" 안내
- 텍스트 늦게 와도 같은 (chat, user) 키로 합쳐서 finalize
- caption 있지만 parse 실패 (보고서 형식 X) 시에도 동일 보존
- **기존**: caption 없으면 silent 폐기 → **변경**: 안전망 + 사용자 안내

### 🧹 메모리 관리 (2026-05-12 추가)
- `/status`: 모듈 레벨 dict 크기 표시 (MENTION/MY_KEYWORD/CHAT/GROUP/PENDING/MEDIA_CACHE)
- `daily_cleanup` (03:30) 에 `cleanup_memory_dicts()` 통합:
  - TRIGGER_HISTORY: 윈도우 밖 timestamp 만 남은 user_id 키 제거
  - CHAT_HISTORY / GROUP_MESSAGES: 빈 list 키 제거
- 1000명 확장 시 cleanup 빈도 / TTL cap 재평가 권장

### 🛡️ 텔레그램 한도 자동 보호 (AIORateLimiter)
- `main.py` ApplicationBuilder 에 `AIORateLimiter(max_retries=3)` 적용
- PTB v22 내장 — 모든 `send_message` / `send_document` 자동 보호
- 한도: 같은 chat 1msg/sec, 그룹 20msg/min, 글로벌 30msg/sec
- 429 에러 시 자동 backoff + retry (최대 3회)
- 적용 범위: mention 알림, 보고서 reply, 서무 DM, /broadcast, 모든 발송

### 보고서 처리 (자동) — 4단 다층 방어

**사용자 권한 체크 의도적으로 없음**.
조직 내부 신뢰 모델 + 4단 보호 + 사후 모니터링.

**Layer 1**: 그룹 진입 — `join_guard` (admin 초대 + `allowed_groups` 27개)
**Layer 2**: 그룹 격리 — 보고서 자동 처리는 `REPORT_GROUP_ID = -1002777848839`
  (총회봉사교통부) 1개 그룹에서만 발생. 나머지 26개 영향 없음.
**Layer 3**: 토픽 격리 — 봉사 / 수상(3553) / MOU(3225) 토픽별 분리
**Layer 4**: 형식 검증 + 트랜잭션 — 키워드 매칭 + alias 필수 필드 + R1.A
  사진 0장 차단 + Word 검증 후 시트 저장

**사후 모니터링 (이상 패턴 감지)**:
- `/weekly_ops` — 주간 운영 점검 + **도배 의심 패턴 감지**
  (사용자별 1주 10건 초과 시 알림, 비admin 만)
- `/myreports` — 사용자별 이력 추적
- `report_log` 8단계 — SQL 로 모든 처리 추적
- `dedup` 알림 — 중복 의심 자동 감지
- 시트 직접 검토 — 서무가 주간 단위로

**위험 발견 시 대응**:
- R1.A 가 자동 차단 (사진 0장)
- 시트 행 수동 삭제 (서무)
- `allowed_groups` 또는 `admin_ids` 조정 (관리자)

### 차단 정책
- 봇 멘션 / `/ai` 비admin 호출: **silent ignore** (스팸 방지)
- `/weekly_ops` 등 명시적 명령어 비admin: "❌ 관리자만 사용 가능합니다"
- 그룹 화이트리스트 외: "❌ 이 그룹에서는 ... 사용할 수 없습니다"

### 🔬 알려진 이슈 / 다음 분석 대상

**알려진 이슈**:
- `notice_handler.broadcast_photo` — PHOTO+CAPTION 핸들러로 등록되지만
  같은 group=0 의 `message_handler.handle_photo_messages` 가 먼저 매칭 →
  **사실상 dead code** (작동 안 함). 사진+`/broadcast` 는 현재 작동 안 됨.
  → 별도 작업으로 group 분리 또는 명령어 형태로 변경 필요.

**다음 분석 후보** (우선순위 순):
1. 보고서 자동 처리 권한 — 도메인 제약만으로 보호되는 케이스 검토
2. `broadcast_photo` 작동 회복 (group 분리 또는 명령어화)
3. `LAST_MENTION` 큐화 (현재는 가장 최근 멘션 1개만, 도배 시 정상 알림 손실)
4. `/sheet` 코드 품질 (하드코딩 인덱스, 컬럼 안전성)

**검토 완료** (안전 확인 또는 정책 적용):
- /sheet (admin 6명), /reply (메인 관리자 1명) — 변경 불필요
- mention_keywords — EXCLUDE_GROUPS + admin 제외로 안전
- my_keywords — 빈도 제한 1시간 3회 적용

**제거된 dead code**:
- `notice_handler.notice_photo` — plugin 등록 없음, 한 번도 호출 안 됨
