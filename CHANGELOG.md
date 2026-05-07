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
