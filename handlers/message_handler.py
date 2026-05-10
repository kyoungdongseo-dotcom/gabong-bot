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

# 사진 먼저 도착했을 때 임시 보관 (텍스트 나중에 올 때 연결용)
PENDING_PHOTOS = {}
PHOTOS_TTL = 600   # 10분 — 여러 앨범 누적 시간 고려
MAX_PHOTOS = 10

# award(3553)/mou(3225) 토픽 — 해당 핸들러가 직접 처리
EXCLUDED_TOPICS = {3553, 3225}

# 5분 후 만료된 MEDIA_GROUP_CACHE 정리
CACHE_TTL = 300


def cleanup_media_cache():
    now = time.time()
    expired = [k for k, v in MEDIA_GROUP_CACHE.items() if now - v.get('created', 0) > CACHE_TTL]
    for k in expired:
        del MEDIA_GROUP_CACHE[k]


def cleanup_pending_photos():
    now = time.time()
    expired = [k for k, v in list(PENDING_PHOTOS.items())
               if now - v.get('created', 0) > PHOTOS_TTL]
    for k in expired:
        PENDING_PHOTOS.pop(k, None)

def get_sheet_service():
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
    return build('sheets', 'v4', credentials=creds)

async def finalize_report(context, report: dict, photos: list, source: str = "",
                          origin: dict = None):
    """봉사보고서 트랜잭션: 사진 → Word → 시트 → DM 전송 → 보고자 reply.
    D-1 엄격: 사진 1장이라도 실패하면 처리 차단."""
    from handlers.report_base import (
        download_photos_batch, with_sheet_retry, send_to_recipient as base_send,
        notify_admin as base_notify, reply_to_origin,
    )
    from handlers.report_docx_handler import generate_docx
    from database import log_report_stage, record_submission
    import os as _os
    from datetime import datetime as _dt
    import pytz as _pytz
    _kst = _pytz.timezone('Asia/Seoul')

    if origin is None:
        origin = report.get('_origin', {}) or {}
    user_id = origin.get('user_id')
    output_path = None
    tmp_files = []
    try:
        loop = asyncio.get_running_loop()

        # ── 1. 사진 다운로드 (D-1 엄격) ────────────────────────────────
        tmp_files, photo_failed = await download_photos_batch(photos[:MAX_PHOTOS])
        log_report_stage(
            'service', 'photos_downloaded',
            'ok' if photo_failed == 0 else 'fail',
            user_id=user_id,
            detail=f"ok={len(tmp_files)} fail={photo_failed}"
        )
        if photo_failed > 0:
            for tmp in tmp_files:
                try: _os.remove(tmp)
                except Exception: pass
            await reply_to_origin(
                context.bot, origin,
                f"❌ 사진 다운로드 실패\n"
                f"사진 {len(photos)}장 중 {photo_failed}장 실패\n"
                f"모든 사진을 다시 보내주세요"
            )
            log_report_stage('service', 'finalize', 'fail',
                             user_id=user_id, detail='photo_failed')
            return

        # ── 2. Word 생성 (사진 경로 전달) ──────────────────────────────
        now_str = _dt.now(_kst).strftime('%Y%m%d_%H%M%S')
        output_path = f"/tmp/report_{now_str}.docx"
        try:
            docx_ok = await loop.run_in_executor(
                None, generate_docx, report, output_path, tmp_files
            )
        except Exception as e:
            docx_ok = False
            print(f"❌ 봉사 Word 생성 예외: {e}")
        log_report_stage('service', 'docx_generated',
                         'ok' if docx_ok else 'fail', user_id=user_id)

        for tmp in tmp_files:
            try: _os.remove(tmp)
            except Exception: pass

        if not docx_ok:
            try:
                if output_path and _os.path.exists(output_path):
                    _os.remove(output_path)
            except Exception: pass
            await reply_to_origin(
                context.bot, origin,
                "❌ Word 파일 생성 실패\n"
                "사진과 보고서를 다시 보내주세요\n"
                "시트 저장도 안 됐습니다"
            )
            log_report_stage('service', 'finalize', 'fail',
                             user_id=user_id, detail='docx_fail')
            return

        # ── 3. 시트 저장 (Word 검증 후) ────────────────────────────────
        for i, url in enumerate(photos[:MAX_PHOTOS], 1):
            report[f'사진{i}링크'] = url
        service = get_sheet_service()
        spreadsheet_id = config.get('spreadsheet_id')
        def _save(data):
            return save_report_to_sheet(data, service, spreadsheet_id)
        try:
            sheet_ok = await loop.run_in_executor(None, with_sheet_retry, _save, report, 3)
        except Exception as e:
            sheet_ok = False
            print(f"⚠️ 봉사 시트 저장 예외: {e}")
        log_report_stage('service', 'sheet_saved',
                         'ok' if sheet_ok else 'fail',
                         user_id=user_id, chat_id=origin.get('chat_id'),
                         topic_id=origin.get('message_thread_id'),
                         message_id=origin.get('message_id'))

        # ── 4. 서무 DM 요약 ────────────────────────────────────────────
        photo_text = f"📸 사진 {len(photos)}장 첨부" if photos else "📸 사진 없음"
        if sheet_ok:
            summary_dm = (
                f"✅ 봉사보고서 처리 완료\n"
                f"📌 {report.get('지파명')} {report.get('교회명')}\n"
                f"📋 {report.get('활동명')}\n"
                f"👥 총 봉사자: {report.get('총봉사자')}명\n"
                f"{photo_text}\n"
                f"📎 출처: {source}"
            )
        else:
            summary_dm = (
                f"⚠️ {report.get('지파명')} {report.get('교회명')} 봉사보고서 - 시트 저장 실패!\n"
                f"Word 파일은 정상이지만 스프레드시트 자동 저장 실패\n"
                f"수동으로 봉사리포트 시트에 추가 부탁드립니다\n\n"
                f"📋 {report.get('활동명')}\n"
                f"👥 총 봉사자: {report.get('총봉사자')}명\n"
                f"{photo_text}\n"
                f"📎 출처: {source}"
            )
        dm_ok = await base_send(context.bot, DOCX_RECIPIENT_ID, text=summary_dm)
        log_report_stage('service', 'recipient_dm_sent',
                         'ok' if dm_ok else 'fail', user_id=user_id)

        # ── 5. Word 파일 전송 ──────────────────────────────────────────
        if output_path and _os.path.exists(output_path):
            jipa = report.get('지파명', '')
            church = report.get('교회명', '')
            activity = report.get('활동명', '')
            date = (report.get('활동일시', '') or '')[:10]
            filename = f"{jipa}_{church}_{activity}_{date}.docx".replace(' ', '_').replace('/', '-')
            try:
                with open(output_path, 'rb') as f:
                    await base_send(
                        context.bot, DOCX_RECIPIENT_ID,
                        document=f, filename=filename,
                        caption=f"📄 새 봉사보고서 Word 파일\n📌 {jipa} {church}\n📋 {activity}\n📅 {date}"
                    )
            finally:
                try: _os.remove(output_path)
                except Exception: pass

        try:
            sub_hash = f"{report.get('지파명', '')}|{report.get('교회명', '')}|{report.get('활동명', '')}"
            record_submission('service', sub_hash, summary_dm[:200])
        except Exception: pass

        # ── 6. 보고자 reply ────────────────────────────────────────────
        if sheet_ok and dm_ok:
            await reply_to_origin(
                context.bot, origin,
                f"✅ 모든 처리 완료\n📸 사진 {len(photos)}장 첨부됨"
            )
        elif sheet_ok and not dm_ok:
            await reply_to_origin(
                context.bot, origin,
                "⚠️ 시트 저장 ✅\n⚠️ 서무 DM 전송 실패 - 관리자에게 알림됨"
            )
        else:
            await reply_to_origin(
                context.bot, origin,
                "⚠️ 시트 저장 실패 - 자동 처리됨\n"
                "Word 파일은 서무에게 정상 전송됐습니다\n"
                "시트는 서무가 수동 추가합니다"
            )
        log_report_stage('service', 'reporter_ack_sent', 'ok', user_id=user_id)
    except Exception as e:
        import traceback
        for tmp in tmp_files:
            try: _os.remove(tmp)
            except Exception: pass
        if output_path:
            try: _os.remove(output_path)
            except Exception: pass
        print(f"❌ 봉사 처리 오류: {e}")
        log_report_stage('service', 'finalize', 'fail', user_id=user_id,
                         detail=str(e)[:200])
        await base_notify(
            context.bot,
            f"❌ 봉사보고서 처리 중 예외 발생: {e}\n"
            f"{traceback.format_exc()[:1000]}"
        )
        await reply_to_origin(
            context.bot, origin,
            f"❌ 처리 중 오류 발생: {str(e)[:200]}\n관리자에게 알림됨"
        )

async def flush_pending_report(context, key):
    """60초 기다린 후 저장. 사진이 계속 오면 5초씩 연장 (최대 5분)"""
    start = time.time()
    await asyncio.sleep(60)
    while True:
        entry = PENDING_REPORTS.get(key)
        if not entry or entry.get('saved'):
            return
        last_photo = entry.get('last_photo_time', 0)
        elapsed = time.time() - start
        if last_photo > 0 and (time.time() - last_photo) < 5 and elapsed < 300:
            await asyncio.sleep(5)
            continue
        break
    entry = PENDING_REPORTS.pop(key, None)
    if not entry or entry.get('saved'):
        return
    entry['saved'] = True
    photo_count = len(entry['photos'])
    print(f"⏳ 사진 대기 완료 → 저장 진행 (사진 {photo_count}장)")
    await finalize_report(context, entry['report'], entry['photos'],
                          source=f"delayed_{photo_count}photos",
                          origin=entry.get('origin'))

async def process_media_group(context, media_group_id: str):
    """앨범 사진 수집 완료 후 처리"""
    await asyncio.sleep(3)
    cache = MEDIA_GROUP_CACHE.get(media_group_id)
    if not cache or cache.get('processed'):
        return
    MEDIA_GROUP_CACHE[media_group_id]['processed'] = True
    caption = cache.get('caption', '')
    photos = cache.get('photos', [])[:MAX_PHOTOS]
    chat_id = cache.get('chat_id')
    user_id = cache.get('user_id')
    origin = cache.get('origin', {})
    pending_key = (chat_id, user_id) if chat_id and user_id else chat_id

    from handlers.report_base import reply_to_origin

    # 텍스트 보고서가 이미 PENDING에 있으면 사진만 연결
    if pending_key in PENDING_REPORTS:
        pending = PENDING_REPORTS.pop(pending_key)
        if not pending.get('saved'):
            pending['saved'] = True
            merged = (pending.get('photos', []) + photos)[:MAX_PHOTOS]
            ignored = max(0, len(pending.get('photos', [])) + len(photos) - MAX_PHOTOS)
            if ignored > 0:
                await reply_to_origin(
                    context.bot, origin,
                    f"⚠️ 사진 {ignored}장 무시됨 (한도 {MAX_PHOTOS}장)"
                )
            await finalize_report(
                context, pending['report'], merged,
                source="album_linked",
                origin=pending.get('origin', origin),
            )
        cleanup_media_cache()
        return

    # 캡션에 보고서 있는 경우
    if caption:
        report = parse_report(caption)
        if report:
            report['_origin'] = origin
            await reply_to_origin(
                context.bot, origin,
                f"✅ 봉사보고서 접수 (사진 {len(photos)}장) - 처리 중"
            )
            await finalize_report(context, report, photos,
                                  source="album_caption", origin=origin)

    cleanup_media_cache()

async def handle_photo_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return
    if update.effective_user.id == config.get('bot_user_id'):
        return
    chat_id = update.effective_chat.id
    if chat_id != REPORT_GROUP_ID:
        return
    thread_id = update.message.message_thread_id
    # award/mou 토픽은 각 전용 핸들러가 처리
    if thread_id in EXCLUDED_TOPICS:
        return

    from handlers.report_base import make_origin, reply_to_origin
    user_id = update.effective_user.id
    origin = make_origin(update)
    pending_key = (chat_id, user_id)

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
                'user_id': user_id,
                'origin': origin,
                'processed': False,
                'created': time.time()
            }
            asyncio.create_task(process_media_group(context, media_group_id))
        MEDIA_GROUP_CACHE[media_group_id]['photos'].append(photo_url)
        if caption:
            MEDIA_GROUP_CACHE[media_group_id]['caption'] = caption
    else:
        # 케이스 B: 사진 1장+캡션 → 즉시 처리
        if caption:
            report = parse_report(caption)
            if report:
                report['_origin'] = origin
                await reply_to_origin(context.bot, origin, "✅ 봉사보고서 접수 - 처리 중")
                await finalize_report(context, report, [photo_url],
                                      source="single_photo_caption", origin=origin)
                return

        from handlers.report_base import add_photos_to_pending, format_photo_count_msg

        # 케이스 C/D/G: 텍스트 후 사진 도착 → PENDING 보고서에 누적
        if pending_key in PENDING_REPORTS and not PENDING_REPORTS[pending_key].get('saved'):
            added, total, ignored = add_photos_to_pending(
                PENDING_REPORTS, pending_key, [photo_url], MAX_PHOTOS
            )
            if added > 0:
                PENDING_REPORTS[pending_key]['last_photo_time'] = time.time()
            await reply_to_origin(context.bot, origin, format_photo_count_msg(total, ignored))
            return

        # 케이스 F: 사진 먼저 도착 → PENDING_PHOTOS 누적
        cleanup_pending_photos()
        added, total, ignored = add_photos_to_pending(
            PENDING_PHOTOS, pending_key, [photo_url], MAX_PHOTOS,
            init_extra={'created': time.time()}
        )
        await reply_to_origin(context.bot, origin, format_photo_count_msg(total, ignored))

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

    if chat_id == REPORT_GROUP_ID and thread_id not in EXCLUDED_TOPICS:
        report = parse_report(text)
        if report:
            from handlers.report_base import make_origin, reply_to_origin
            from database import log_report_stage
            origin = make_origin(update)
            pending_key = (chat_id, user_id)

            log_report_stage('service', 'received', 'ok',
                             user_id=user_id, chat_id=chat_id,
                             topic_id=thread_id,
                             message_id=update.message.message_id,
                             detail=text[:120])
            log_report_stage('service', 'parsed', 'ok', user_id=user_id,
                             detail=f"{report.get('지파명','')} | {report.get('활동명','')}")

            # 케이스 F/G: 먼저 도착한 사진 연결
            pre_photos: list = []
            if pending_key in PENDING_PHOTOS:
                pre_photos = PENDING_PHOTOS.pop(pending_key)['photos']

            report['_origin'] = origin
            PENDING_REPORTS[pending_key] = {
                'report': report,
                'photos': pre_photos,
                'saved': False,
                'last_photo_time': time.time() if pre_photos else 0,
                'origin': origin,
            }

            photo_msg = f" (이미 받은 사진 {len(pre_photos)}장 포함)" if pre_photos else ""
            await reply_to_origin(
                context.bot, origin,
                f"✅ 봉사보고서 접수{photo_msg}\n사진 대기 중 (60s+ 추가 5분 자동 연장)"
            )
            asyncio.create_task(flush_pending_report(context, pending_key))
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
