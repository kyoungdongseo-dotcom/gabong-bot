from telegram import Update
from telegram.ext import ContextTypes
import asyncio
import time
import config
from utils import ask_claude, get_chat_mode, log_message, GROUP_MESSAGES, LAST_MENTION, save_last_mention
from handlers.report_parser import parse_report, save_report_to_sheet
from handlers.report_docx_handler import generate_and_send_docx
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

AUTHORIZED_USERS = set(config.get('admin_ids') or [])

REPORT_GROUP_ID = -1002777848839
DOCX_RECIPIENT_ID = 754270008
MEDIA_GROUP_CACHE = {}

# 텍스트 보고서 임시 저장 (사진 나중에 올 때 연결용)
PENDING_REPORTS = {}

# 5분 후 만료된 MEDIA_GROUP_CACHE 정리
CACHE_TTL = 300

def cleanup_media_cache():
    now = time.time()
    expired = [k for k, v in MEDIA_GROUP_CACHE.items() if now - v.get('created', 0) > CACHE_TTL]
    for k in expired:
        del MEDIA_GROUP_CACHE[k]

def get_sheet_service():
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
    return build('sheets', 'v4', credentials=creds)

async def finalize_report(context, report: dict, photos: list, source: str = ""):
    """보고서 최종 저장 + Word 전송"""
    for i, url in enumerate(photos[:5], 1):
        report[f'사진{i}링크'] = url
    try:
        service = get_sheet_service()
        spreadsheet_id = config.get('spreadsheet_id')
        success = save_report_to_sheet(report, service, spreadsheet_id)
        if success:
            photo_text = f"📸 사진 {len(photos)}장 링크 저장 완료" if photos else "📸 사진 없음"
            await context.bot.send_message(
                chat_id=DOCX_RECIPIENT_ID,
                text=(
                    f"✅ 봉사보고서 자동 저장 완료!\n"
                    f"📌 {report.get('지파명')} {report.get('교회명')}\n"
                    f"📋 {report.get('활동명')}\n"
                    f"👥 총 봉사자: {report.get('총봉사자')}명\n"
                    f"{photo_text}\n"
                    f"📎 출처: {source}"
                )
            )
            await generate_and_send_docx(context.bot, DOCX_RECIPIENT_ID, report)
    except Exception as e:
        print(f"❌ 보고서 저장 오류: {e}")

async def flush_pending_report(context, chat_id: int):
    """30초 대기 후 저장 (사진 도착할 때마다 타이머 리셋)"""
    await asyncio.sleep(30)
    entry = PENDING_REPORTS.get(chat_id)
    if not entry or entry.get('saved'):
        return
    # 마지막 사진 도착 후 5초 이상 지났는지 확인
    last_photo_time = entry.get('last_photo_time', 0)
    if last_photo_time > 0 and (time.time() - last_photo_time) < 5:
        # 아직 사진 올리는 중 → 5초 더 대기
        await asyncio.sleep(5)
    entry = PENDING_REPORTS.pop(chat_id, None)
    if not entry or entry.get('saved'):
        return
    entry['saved'] = True
    photo_count = len(entry['photos'])
    print(f"⏳ 사진 대기 완료 → 저장 진행 (사진 {photo_count}장)")
    await finalize_report(context, entry['report'], entry['photos'], source=f"delayed_{photo_count}photos")

async def process_media_group(context, media_group_id: str):
    """앨범 사진 수집 완료 후 처리"""
    await asyncio.sleep(3)
    cache = MEDIA_GROUP_CACHE.get(media_group_id)
    if not cache or cache.get('processed'):
        return
    MEDIA_GROUP_CACHE[media_group_id]['processed'] = True
    caption = cache.get('caption', '')
    photos = cache.get('photos', [])[:5]
    chat_id = cache.get('chat_id')

    # 텍스트 보고서가 이미 PENDING에 있으면 사진만 연결
    if chat_id and chat_id in PENDING_REPORTS:
        pending = PENDING_REPORTS.pop(chat_id)
        if not pending.get('saved'):
            pending['saved'] = True
            await finalize_report(context, pending['report'], photos, source="album_linked")
        return

    # 캡션에 보고서 있는 경우
    if caption:
        report = parse_report(caption)
        if report:
            await finalize_report(context, report, photos, source="album_caption")

    cleanup_media_cache()

async def handle_photo_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return
    if update.effective_user.id == config.get('bot_user_id'):
        return
    chat_id = update.effective_chat.id
    if chat_id != REPORT_GROUP_ID:
        return

    caption = update.message.caption or ""
    media_group_id = update.message.media_group_id

    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_url = photo_file.file_path

    if media_group_id:
        if media_group_id not in MEDIA_GROUP_CACHE:
            MEDIA_GROUP_CACHE[media_group_id] = {
                'caption': '',
                'photos': [],
                'chat_id': chat_id,
                'processed': False,
                'created': time.time()
            }
            asyncio.create_task(process_media_group(context, media_group_id))
        MEDIA_GROUP_CACHE[media_group_id]['photos'].append(photo_url)
        if caption:
            MEDIA_GROUP_CACHE[media_group_id]['caption'] = caption
    else:
        # 사진 1장, 캡션에 보고서 있는 경우
        if caption:
            report = parse_report(caption)
            if report:
                await finalize_report(context, report, [photo_url], source="single_photo_caption")
                return

        # 캡션 없이 사진만 → PENDING 보고서에 연결
        if chat_id in PENDING_REPORTS and not PENDING_REPORTS[chat_id].get('saved'):
            PENDING_REPORTS[chat_id]['photos'].append(photo_url)
            PENDING_REPORTS[chat_id]['last_photo_time'] = time.time()
            print(f"📸 사진 추가 (현재 {len(PENDING_REPORTS[chat_id]['photos'])}장)")
            # 사진이 5장 모이면 바로 저장
            if len(PENDING_REPORTS[chat_id]['photos']) >= 5:
                entry = PENDING_REPORTS.pop(chat_id)
                entry['saved'] = True
                await finalize_report(context, entry['report'], entry['photos'], source="max_photos")

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.effective_user.id == config.get('bot_user_id'):
        return
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    text = update.message.text
    thread_id = update.message.message_thread_id
    print(f"그룹 ID: {chat_id} | 토픽 ID: {thread_id} | 그룹명: {update.message.chat.title} | 메시지: {text}")

    log_message(chat_id, user_id, user_name, "user", text, thread_id)
    if chat_id not in GROUP_MESSAGES:
        GROUP_MESSAGES[chat_id] = []
    GROUP_MESSAGES[chat_id].append(f"{user_name}: {text}")
    if len(GROUP_MESSAGES[chat_id]) > 100:
        GROUP_MESSAGES[chat_id] = GROUP_MESSAGES[chat_id][-100:]

    if chat_id == REPORT_GROUP_ID:
        report = parse_report(text)
        if report:
            PENDING_REPORTS[chat_id] = {
                'report': report,
                'photos': [],
                'saved': False,
                'last_photo_time': 0
            }
            asyncio.create_task(flush_pending_report(context, chat_id))
            return

    MY_KEYWORDS = config.get('my_keywords')
    my_keyword_found = any(kw in text for kw in MY_KEYWORDS)
    if my_keyword_found and update.effective_user.id != config.get('my_user_id'):
        group_name = update.message.chat.title or "그룹"
        sender = update.effective_user.first_name
        LAST_MENTION[config.get('my_user_id')] = {
            "chat_id": chat_id,
            "message_id": update.message.message_id
        }
        save_last_mention(LAST_MENTION)
        await context.bot.send_message(
            chat_id=config.get('my_user_id'),
            text=f"📣 멘션/호출 알림!\n\n그룹: {group_name}\n보낸 사람: {sender}\n내용: {text}\n\n답변하려면: /reply [내용]"
        )

    MENTION_KEYWORDS = config.get('mention_keywords')
    EXCLUDE_GROUPS = config.get('exclude_groups')
    TOPIC_IDS = config.get('topic_ids')
    PARTIAL_EXCLUDE = config.get('partial_exclude_groups') or {}
    for keyword, topic_name in MENTION_KEYWORDS.items():
        if keyword in text and update.effective_user.id not in AUTHORIZED_USERS and chat_id not in EXCLUDE_GROUPS:
            # 부분 제외 그룹 처리
            partial_keywords = PARTIAL_EXCLUDE.get(str(chat_id), [])
            if partial_keywords and keyword in partial_keywords:
                continue
            group_name = update.message.chat.title or "그룹"
            sender = update.effective_user.first_name
            topic_id = TOPIC_IDS[topic_name]
            await context.bot.send_message(
                chat_id=config.get('group_id'),
                message_thread_id=topic_id,
                text=f"📣 멘션 알림!\n\n그룹: {group_name}\n보낸 사람: {sender}\n내용: {text}"
            )
            break

    bot_username = context.bot.username
    if f"@{bot_username}" in text:
        question = text.replace(f"@{bot_username}", "").strip()
        if not question:
            return
        if "요약" in question and GROUP_MESSAGES.get(chat_id):
            history = "\n".join(GROUP_MESSAGES[chat_id])
            question = f"다음 대화를 한국어로 요약해주세요:\n{history}"
        mode = get_chat_mode(chat_id)
        await update.message.reply_text("🤖 AI가 답변 중입니다...")
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(None, ask_claude, question, chat_id, user_id, user_name, thread_id, mode)
        await update.message.reply_text(f"🤖 AI 답변\n\n{answer}")
