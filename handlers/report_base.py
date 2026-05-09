"""3개 보고서(봉사/MOU/수상) 공통 베이스 유틸리티"""

import asyncio
import os
import tempfile
import time
from datetime import datetime

import pytz
import requests
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import config

KST = pytz.timezone('Asia/Seoul')
ADMIN_USER_ID = 97057565


# ── 텔레그램 통신 ──────────────────────────────────────────────────────────────

async def notify_admin(bot, message: str):
    """관리자 백업 알림 (서무 DM 실패 시 등)"""
    try:
        await bot.send_message(chat_id=ADMIN_USER_ID, text=message[:4000])
    except Exception as e:
        print(f"❌ 관리자 알림 실패: {e}")


async def send_to_recipient(bot, recipient_id: int, retries: int = 3, **kwargs):
    """서무 DM 전송. 실패 시 1초·2초 백오프 후 재시도. 최종 실패 시 관리자 백업."""
    last_err = None
    for attempt in range(retries):
        try:
            if 'document' in kwargs:
                await bot.send_document(chat_id=recipient_id, **kwargs)
            else:
                await bot.send_message(chat_id=recipient_id, **kwargs)
            return True
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)  # 1, 2, 4초
    await notify_admin(
        bot,
        f"❌ 서무({recipient_id}) DM {retries}회 실패: {last_err}\n"
        f"내용: {str(kwargs.get('text', ''))[:300]}"
    )
    return False


async def reply_to_origin(bot, origin: dict, text: str) -> bool:
    """보고자 원본 메시지에 답글. origin = {chat_id, message_id, message_thread_id}"""
    if not origin or not origin.get('chat_id') or not origin.get('message_id'):
        return False
    try:
        kwargs = {
            'chat_id': origin['chat_id'],
            'text': text[:4000],
            'reply_to_message_id': origin['message_id'],
        }
        if origin.get('message_thread_id'):
            kwargs['message_thread_id'] = origin['message_thread_id']
        await bot.send_message(**kwargs)
        return True
    except Exception as e:
        print(f"⚠️ 보고자 답글 실패: {e}")
        return False


def make_origin(update) -> dict:
    """telegram Update에서 보고자 메시지 위치 추출"""
    if not update or not update.message:
        return {}
    return {
        'chat_id': update.effective_chat.id,
        'message_id': update.message.message_id,
        'message_thread_id': update.message.message_thread_id,
        'user_id': update.effective_user.id if update.effective_user else None,
    }


def with_sheet_retry(save_fn, data, retries: int = 3) -> bool:
    """시트 저장 재시도. 실패 시 1·2·4초 백오프."""
    for attempt in range(retries):
        try:
            if save_fn(data):
                return True
        except Exception as e:
            print(f"⚠️ 시트 저장 attempt {attempt+1} 실패: {e}")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    return False


def format_alias_hint(field: str, aliases_dict: dict) -> str:
    aliases = aliases_dict.get(field, [field])
    return f"{field} (다음 중 하나로 입력 가능: {', '.join(aliases)})"


# ── 사진 다운로드 ──────────────────────────────────────────────────────────────

def download_photo(url: str, retries: int = 3, delay: int = 5) -> str | None:
    """사진 다운로드 (최대 retries회, 실패 시 delay초 대기 후 재시도)"""
    token = config.get('telegram_token')
    full_url = url if url.startswith('http') else f"https://api.telegram.org/file/bot{token}/{url}"
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(full_url, timeout=10)
            if resp.status_code == 200:
                suffix = '.jpg' if 'jpg' in url.lower() else '.png'
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(resp.content)
                tmp.close()
                return tmp.name
            last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = str(e)
        if attempt < retries - 1:
            time.sleep(delay)
    print(f"❌ 사진 다운로드 {retries}회 모두 실패 ({last_err}): {url[:60]}")
    return None


async def download_photos_batch(photo_urls: list) -> tuple:
    """사진 다운로드. 반환: (성공 임시파일 리스트, 실패 개수)"""
    loop = asyncio.get_running_loop()
    tmp_files = []
    failed = 0
    for url in photo_urls:
        if not url:
            continue
        tmp = await loop.run_in_executor(None, download_photo, url)
        if tmp:
            tmp_files.append(tmp)
        else:
            failed += 1
    return tmp_files, failed


# ── Word docx 헬퍼 ─────────────────────────────────────────────────────────────

def set_cell_bg(cell, color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    tcPr.append(shd)


def docx_label(cell, text: str):
    cell.text = text
    run = cell.paragraphs[0].runs[0]
    run.bold = True
    run.font.size = Pt(10)
    set_cell_bg(cell, 'D5E8F0')


def docx_value(cell, text: str):
    cell.text = text or '-'
    cell.paragraphs[0].runs[0].font.size = Pt(10)


def add_photos_grid(doc, photo_paths: list, title: str = '사진'):
    """사진 2열 그리드 (8cm x 5cm). 1페이지에 4장."""
    if not photo_paths:
        return
    p = doc.add_paragraph()
    run = p.add_run(title)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(8)
    for i in range(0, len(photo_paths), 2):
        pair = photo_paths[i:i+2]
        photo_table = doc.add_table(rows=1, cols=len(pair))
        for j, path in enumerate(pair):
            cell = photo_table.rows[0].cells[j]
            try:
                para = cell.paragraphs[0]
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                pic_run = para.add_run()
                pic_run.add_picture(path, width=Cm(8), height=Cm(5))
            except Exception as e:
                print(f"❌ 사진 삽입 오류: {e}")
                cell.paragraphs[0].add_run("사진 오류")
        doc.add_paragraph()


# ── PENDING 대기 관리 ──────────────────────────────────────────────────────────

def cleanup_pending_photos(pending_dict: dict, ttl: int = 300):
    now = time.time()
    expired = [k for k, v in list(pending_dict.items())
               if now - v.get('created', 0) > ttl]
    for k in expired:
        pending_dict.pop(k, None)


# 보고서당 최대 사진 수
MAX_PHOTOS = 10


def add_photos_to_pending(pending_dict: dict, key, new_photos: list,
                          max_total: int = MAX_PHOTOS,
                          init_extra: dict = None) -> tuple:
    """
    pending_dict[key]['photos']에 사진 누적, max_total 도달 시 무시.
    pending_dict[key] 없으면 생성 (init_extra로 추가 필드 설정 가능).
    Returns: (added_count, total_after, ignored_count)
    """
    if key not in pending_dict:
        pending_dict[key] = {'photos': []}
        if init_extra:
            pending_dict[key].update(init_extra)
    current_photos = pending_dict[key]['photos']
    if len(current_photos) >= max_total:
        return 0, len(current_photos), len(new_photos)
    can_add = max_total - len(current_photos)
    to_add = new_photos[:can_add]
    current_photos.extend(to_add)
    return len(to_add), len(current_photos), len(new_photos) - len(to_add)


def format_photo_count_msg(total: int, ignored: int = 0,
                            max_total: int = MAX_PHOTOS) -> str:
    """사진 누적 카운트 메시지"""
    if total >= max_total and ignored > 0:
        return f"📸 {total}/{max_total}장 접수 (추가 {ignored}장 무시됨)"
    if total >= max_total:
        return f"📸 {total}/{max_total}장 접수 (이후 추가 사진은 무시됩니다)"
    return f"📸 {total}/{max_total}장 접수"


async def flush_pending_generic(
    pending_dict: dict,
    key,
    finalize_callback,
    initial_wait: int = 60,
    max_wait: int = 300,
    photo_idle: int = 5,
):
    """공통 flush: 60초 후 사진 idle 5초까지 연장 (max_wait까지)"""
    start = time.time()
    await asyncio.sleep(initial_wait)
    while True:
        entry = pending_dict.get(key)
        if not entry or entry.get('saved'):
            return
        last_photo = entry.get('last_photo_time', 0)
        elapsed = time.time() - start
        if last_photo > 0 and (time.time() - last_photo) < photo_idle and elapsed < max_wait:
            await asyncio.sleep(photo_idle)
            continue
        break
    entry = pending_dict.pop(key, None)
    if not entry or entry.get('saved'):
        return
    entry['saved'] = True
    await finalize_callback(entry)


# ── 앨범(media_group) 처리 ────────────────────────────────────────────────────

async def process_album_generic(
    media_group_id: str,
    cache: dict,
    on_complete,
    wait_seconds: int = 3,
):
    """앨범 사진 모두 도착 대기 후 콜백 호출.
    cache[media_group_id] = {'photos': list, 'caption': str, 'processed': bool, 'created': float, ...}
    on_complete(entry) 호출.
    """
    await asyncio.sleep(wait_seconds)
    entry = cache.get(media_group_id)
    if not entry or entry.get('processed'):
        return
    cache[media_group_id]['processed'] = True
    try:
        await on_complete(entry)
    finally:
        # TTL 만료된 캐시 정리
        now = time.time()
        expired = [k for k, v in list(cache.items()) if now - v.get('created', 0) > 300]
        for k in expired:
            cache.pop(k, None)


# ── 공통 finalize ─────────────────────────────────────────────────────────────

async def finalize_generic(
    bot,
    *,
    data: dict,
    photos: list,
    name: str,
    name_emoji: str,
    recipient_id: int,
    save_to_sheet,
    generate_docx,
    docx_filename_fn,
    summary_fn,
    output_prefix: str,
):
    """3개 보고서 공통 finalize.
    save_to_sheet(data) -> bool
    generate_docx(data, list_of_photo_paths, output_path) -> bool
    docx_filename_fn(data) -> str
    summary_fn(data) -> str
    """
    try:
        # 사진 URL을 사진1~5링크로 저장
        for i in range(1, 6):
            data[f'사진{i}링크'] = photos[i-1] if i <= len(photos) else ''

        loop = asyncio.get_running_loop()

        # 시트 저장
        try:
            sheet_ok = await loop.run_in_executor(None, save_to_sheet, data)
        except Exception as e:
            sheet_ok = False
            print(f"❌ {name} 시트 저장 예외: {e}")

        # 사진 다운로드 (병렬)
        tmp_files, photo_failed = await download_photos_batch(photos[:5])

        # Word 생성
        now_str = datetime.now(KST).strftime('%Y%m%d_%H%M%S')
        output_path = f"/tmp/{output_prefix}_{now_str}.docx"
        try:
            docx_ok = await loop.run_in_executor(
                None, generate_docx, data, tmp_files, output_path
            )
        except Exception as e:
            docx_ok = False
            print(f"❌ {name} Word 생성 예외: {e}")

        for tmp in tmp_files:
            try:
                os.remove(tmp)
            except Exception:
                pass

        # 요약
        body = summary_fn(data)
        emoji = '✅' if sheet_ok else '⚠️'
        summary = f"{emoji} {name} 처리 결과\n{body}"
        warnings = []
        if not sheet_ok:
            warnings.append("스프레드시트 저장 실패 — 수동 저장 필요")
        if not docx_ok:
            warnings.append("Word 파일 생성 실패 — 텍스트만 저장됨")
        if photo_failed > 0:
            warnings.append(f"사진 {photo_failed}장 다운로드 실패 (파일 링크 만료 가능)")
        if photos:
            summary += f"\n\n📸 사진 {len(photos)}장 첨부"
        if warnings:
            summary += "\n\n⚠️ " + "\n⚠️ ".join(warnings)

        await send_to_recipient(bot, recipient_id, text=summary)

        # Word 파일 전송
        if docx_ok and os.path.exists(output_path):
            try:
                with open(output_path, 'rb') as f:
                    await send_to_recipient(
                        bot, recipient_id,
                        document=f,
                        filename=docx_filename_fn(data),
                        caption=f"{name_emoji} {name} Word 파일"
                    )
            finally:
                try:
                    os.remove(output_path)
                except Exception:
                    pass
    except Exception as e:
        import traceback
        await notify_admin(
            bot,
            f"❌ {name} 처리 중 예외 발생: {e}\n"
            f"데이터: {str(data)[:300]}\n"
            f"{traceback.format_exc()[:1000]}"
        )


# ── 시간 헬퍼 ──────────────────────────────────────────────────────────────────

def now_kst_str(fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    return datetime.now(KST).strftime(fmt)


def now_kst_filename() -> str:
    return datetime.now(KST).strftime('%Y%m%d_%H%M%S')
