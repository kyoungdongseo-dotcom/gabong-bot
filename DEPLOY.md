# 가봉봇 Railway 배포 가이드

노트북 꺼져 있어도 24/7 작동하도록 Railway 클라우드에 배포하는 전체 절차입니다.

---

## 사전 준비 (각 5분)

- GitHub 계정 ([https://github.com](https://github.com))
- Railway 계정 ([https://railway.app](https://railway.app))
- 신용카드 (Railway 요금 월 $5 정도, 사용량 기반 과금)

---

## 1단계. GitHub 레포지토리 만들기

### 1-1. 로컬에서 Git 초기화

터미널에서:

```bash
cd /Users/seogyeongdong/gabong-bot

# Git 저장소로 초기화
git init

# .gitignore 로 제외된 파일 확인 (venv, .env 등이 보이면 안 됨)
git status

# 전체 파일 스테이징
git add .

# 첫 커밋
git commit -m "Initial commit: 가봉봇 Railway 배포 준비"
```

### 1-2. GitHub 에서 빈 레포지토리 생성

1. [https://github.com/new](https://github.com/new) 접속
2. Repository name: `gabong-bot` (원하는 이름)
3. **Private 선택** (토큰이 `.env` 에 있어서 안전하지만, 만약을 위해 private 권장)
4. README/gitignore/license 체크박스는 **전부 비우기** (로컬에 이미 있음)
5. "Create repository" 클릭

### 1-3. 로컬 코드를 GitHub 로 푸시

GitHub 가 만들어준 안내 페이지의 "push an existing repository" 명령어를 복사해서 실행. 보통 이런 형태:

```bash
git remote add origin https://github.com/당신계정/gabong-bot.git
git branch -M main
git push -u origin main
```

푸시 끝나면 GitHub 레포에 `bot.py`, `requirements.txt` 등이 보여야 해요.

**중요**: `.env` 파일이 **절대 업로드되면 안 됩니다**. 푸시 후 GitHub 에서 파일 목록 확인하세요. 혹시 보이면 즉시 `.gitignore` 체크하고 다시 작업.

---

## 2단계. Railway 프로젝트 생성

### 2-1. Railway 로그인

[https://railway.app](https://railway.app) → "Login" → GitHub 계정으로 로그인

### 2-2. 새 프로젝트 생성

1. 대시보드에서 "New Project" 클릭
2. "Deploy from GitHub repo" 선택
3. GitHub 연동 안 되어 있으면 "Configure GitHub App" 으로 Railway 에 레포 접근 권한 부여
4. 방금 만든 `gabong-bot` 레포 선택
5. "Deploy Now" 클릭

Railway 가 자동으로 `requirements.txt` 를 감지하고 빌드를 시작합니다. 약 2~3분 소요.

---

## 3단계. 환경변수 설정

빌드 끝나면 첫 실행 때 `TELEGRAM_TOKEN` 이 없어서 봇이 죽을 거예요. 환경변수 넣어야 합니다.

### 3-1. Variables 탭 열기

1. Railway 프로젝트 화면에서 서비스 카드 클릭
2. 상단 탭 중 "Variables" 클릭
3. "New Variable" 또는 "Raw Editor" 클릭

### 3-2. 환경변수 일괄 입력 (Raw Editor 추천)

Raw Editor 에 아래 내용 붙여넣기:

```
TELEGRAM_TOKEN=8740092962:AAHnR-u7qcWyhQdIC9tVvCbh41pEBFavu58
GROUP_ID=-1002363981206
TOPIC_ID=2
ADMIN_IDS=97057565
REMINDERS_FILE=/data/reminders.json
```

`REMINDERS_FILE=/data/reminders.json` 이 중요한 부분이에요. 이 경로는 다음 단계에서 만들 Volume 에 마운트됩니다.

"Update Variables" 저장.

---

## 4단계. Volume 설정 (데이터 영속화)

**이 단계를 빼먹으면 리마인더 데이터가 매 배포마다 날아갑니다.**

### 4-1. Volume 추가

1. 서비스 화면에서 "Settings" 또는 "Volumes" 탭
2. "New Volume" 클릭
3. Mount Path: `/data` (env var 에 지정한 경로와 일치시켜야 함)
4. 크기: 기본값 (1GB) 충분
5. 저장

Railway 가 Volume 붙이고 재배포합니다.

### 4-2. 기존 reminders.json 업로드 (선택)

이미 등록한 리마인더가 있다면, Railway 배포 후에 로컬 `reminders.json` 내용을 Volume 에 복사해야 해요.

방법 A: **텔레그램에서 다시 등록**이 가장 간단. 어차피 지금 남은 건 2개뿐이에요.

방법 B: Railway CLI 로 파일 업로드 (더 번거로움):
```bash
npm install -g @railway/cli
railway login
railway link  # 프로젝트 연결
railway run cp reminders.json /data/reminders.json
```

---

## 5단계. 배포 확인

### 5-1. 로그 확인

서비스 화면에서 "Deployments" → 최신 배포 클릭 → "View Logs"

이런 로그가 나와야 정상:
```
저장된 리마인드 0개 복원 완료
봇 시작!
```

### 5-2. 텔레그램에서 작동 확인

텔레그램에서:
```
/start
```

봇이 응답하면 배포 성공 ✅

---

## 6단계. 로컬 봇 종료

Railway 에서 잘 도는 걸 확인했으면, **맥에서 돌리던 봇은 꼭 종료**하세요.

양쪽에서 동시에 돌면 같은 리마인더가 두 번 발송되거나 텔레그램 API 가 충돌합니다.

맥 터미널에서 봇 실행 중이던 창에 `Control+C`.

---

## 운영 팁

### 로그 보기

Railway 웹 UI 에서 실시간 로그 확인 가능. 에러가 나면 여기서 바로 보여요.

### 업데이트 방법

코드 수정하고 싶을 때:

```bash
cd /Users/seogyeongdong/gabong-bot
# 코드 수정
git add .
git commit -m "설명"
git push
```

푸시하면 Railway 가 자동으로 감지해서 재배포합니다. 3분 정도 걸려요.

### 비용 모니터링

Railway 대시보드 → Usage 에서 이번 달 사용량 확인. 소규모 봇 기준 월 $3~5 범위.

### 봇이 갑자기 안 될 때 체크리스트

1. Railway 대시보드에서 서비스 상태 확인 (Running 인가?)
2. Logs 에서 에러 메시지 확인
3. `TELEGRAM_TOKEN` 이 여전히 유효한지 (BotFather 에서 재확인)
4. 볼륨이 마운트돼 있는지 (Settings → Volumes)

### 토큰 재발급이 필요할 때

혹시 토큰이 노출된 것 같으면:
1. 텔레그램에서 `@BotFather` → `/token` → 봇 선택 → `/revoke`
2. 새 토큰 발급
3. Railway Variables 탭에서 `TELEGRAM_TOKEN` 값 업데이트
4. `.env` 파일의 로컬 토큰도 업데이트 (아직 로컬에서 쓰는 경우)

---

## 문제 발생 시

로그 메시지를 복사해서 제(Claude)한테 보여주세요. 바로 진단해드립니다.
