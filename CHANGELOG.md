# CHANGELOG
# CHANGELOG
# 모든 주목할 만한 변경사항이 이 파일에 기록됩니다.

---

## [2026-05-07]

### ✨ 추가
- **SQLite 도입** (database.py)
  - 리마인더 영구 저장 (reminders.json 리셋 문제 해결)
  - messages, bot_state, error_logs 테이블 추가
  - migrate.py로 JSON → SQLite 마이그레이션 지원

- **봉사달력 자동감지** (weekly_schedule_handler.py)
  - get_current_service_sheet_name() 함수 추가
  - 매달 새로운 시트를 자동으로 감지
  - 수동 config 수정 불필요

### 🔧 수정
- **reaction_handler.py**: 총회봉사교통부(-1002363981206) 내부 반응 제외
  - 같은 그룹 내 반응이 다시 전달되는 문제 해결

- **weekly_schedule_handler.py**: 총회스케줄 범위 확대
  - council_schedule_range: "B44:H54" → "B44:M80"
  - 5월뿐만 아니라 여러 달 데이터 지원

- **reminder_handler.py**: database.py 함수로 변경
  - load_reminders/save_reminders → database 함수 사용
  - JSON 파일 사용 제거

### ⚠️ 주의사항
- /data/reminders.json이 있으면 migrate.py 실행 필요
- Railway 배포 시 /data 볼륨이 있어야 SQLite 작동
- 로컬은 ./data 디렉토리 자동 생성

### 🐛 해결된 문제
- **리셋 문제**: JSON → SQLite (1-2시간 리셋 문제 완전 해결)
- **반응 중복 전달**: 총회봉사교통부 내부 반응 제외
- **달마다 수정 필요**: 봉사달력 자동감지

---

## [2026-05-06]

### 🔧 수정
- **schedule 명령어**: 총회스케줄 구조 재확인
  - B44: 요일, B45: 일자, B46: 내용
  - A열이 아니라 B열임 (메모리 오류 정정)

### 📝 메모리 정정
- council_schedule_sheet_name: "2026년 총회 업무일정" (확인)
- 총회스케줄 구조 정확히 파악

---

## 알려진 문제

### ✅ 해결된 문제
- [x] 리마인더 데이터 리셋 (SQLite 도입)
- [x] 총회봉사교통부 반응 중복 전달
- [x] 봉사달력 월별 수동 수정

### ⏳ 예정된 개선
- [ ] 테스트 코드 작성 (test_suite.py)
- [ ] staging 브랜치 운영
- [ ] 에러 로깅 강화

---

## 개발 프로세스

\`\`\`bash
# 수정 전 필수
python3 -m py_compile 파일명.py  # ✅ OK 확인

# 수정 후 필수
git add 파일명
git commit -m "feat/fix: 설명"
git push

# Railway 자동 배포
\`\`\`

---

## [2026-05-07] 2차 업데이트

### ✨ 추가
- **봉사보고서 자동 파싱** (report_parser.py)
  - 텍스트 보고서 자동 감지 및 파싱
  - 사진 5장 링크 저장
  - 스프레드시트 봉사리포트 시트 자동 저장

- **주간 봉사 분석 리포트** (weekly_report_analyzer.py)
  - 매주 월요일 08:00 관리자 DM 자동 발송
  - 봉사건수, 봉사자, 수혜자, 분류별 통계

- **월간통계 자동화** (monthly_stats_handler.py)
  - 매월 1일 00:00 자동 집계
  - 월간통계 시트 자동 저장
  - 관리자 DM 발송

- **/report 명령어** - 즉시 주간 분석 리포트 확인
- **/monthly 명령어** - 즉시 월간통계 확인
- **봇 명령어 자동 등록** - 시작 시 자동으로 메뉴 등록

### 🔧 수정
- **message_handler.py**: 사진 앨범(5장) 처리 추가
- **message_plugin.py**: 사진 메시지 핸들러 등록
- **main.py**: 월간통계 스케줄러 추가

### 📊 스프레드시트 구조
- 봉사리포트 시트: A~W열 (23개 필드)
- 월간통계 시트: A~M열 (13개 필드)

### 🗓️ 자동화 스케줄
- 매일 20:00 → 대화 요약 DM
- 매주 월요일 08:00 → 주간 봉사 분석 DM
- 매월 1일 00:00 → 월간통계 DM + 시트 저장
