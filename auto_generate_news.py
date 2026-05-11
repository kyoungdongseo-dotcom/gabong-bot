"""
세계경제 뉴스 카드 자동 생성 시스템
매일 월~금에 실행되는 자동화 스크립트
"""

import json
import os
from datetime import datetime, timedelta
import subprocess
import sys

# 설정
OUTPUT_BASE_DIR = "/Users/seogyeongdong/gabong-bot"
DATA_FILE = "/Users/seogyeongdong/gabong-bot/news_data.json"

def get_date_folder():
    """현재 날짜 기반 폴더 경로 생성"""
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    
    folder_name = f"세계경제뉴스_{year}년{month}월{day}일"
    folder_path = os.path.join(OUTPUT_BASE_DIR, folder_name)
    
    return folder_path, folder_name

def create_directory(path):
    """디렉토리 생성"""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"✓ 폴더 생성: {path}")
    return path

def load_news_data():
    """뉴스 데이터 로드"""
    if not os.path.exists(DATA_FILE):
        print(f"⚠️ 데이터 파일 없음: {DATA_FILE}")
        return None
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return None

def generate_html_cover(date_str, summary, quote):
    """커버 카드 HTML 생성"""
    accent = "#38BDF8"
    BG = "#08080F"
    CARD_BG = "#0D0D18"
    
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>세계경제 뉴스</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ 
      background: {BG}; 
      font-family: 'Georgia','Times New Roman',serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 20px;
    }}
    .card {{
      width: 340px;
      height: 340px;
      background: {CARD_BG};
      border-radius: 22px;
      padding: 30px 28px;
      position: relative;
      overflow: hidden;
      border: 1px solid {accent}28;
      box-shadow: 0 0 0 1px {accent}28, 0 20px 70px rgba(0,0,0,.85), 0 0 50px {accent}18;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .top-stripe {{
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, transparent, {accent}, transparent);
    }}
    .glow {{
      position: absolute;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: radial-gradient(circle, {accent}1A 0%, transparent 70%);
      top: 20px;
      right: 20px;
      pointer-events: none;
    }}
    .header {{
      position: relative;
      z-index: 1;
    }}
    .label {{
      font-size: 8px;
      letter-spacing: 4px;
      color: {accent};
      font-family: 'Courier New', monospace;
      margin-bottom: 14px;
      text-transform: uppercase;
    }}
    .title {{
      font-size: 44px;
      font-weight: 900;
      color: #fff;
      line-height: 1.0;
      white-space: pre-line;
    }}
    .subtitle {{
      font-size: 9px;
      letter-spacing: 5px;
      color: #222;
      font-family: 'Courier New', monospace;
      margin-top: 8px;
      text-transform: uppercase;
    }}
    .summary-box {{
      background: #ffffff08;
      border-radius: 10px;
      padding: 12px 14px;
      border: 1px solid {accent}22;
    }}
    .summary-label {{
      font-size: 8px;
      letter-spacing: 3px;
      color: {accent};
      font-family: 'Courier New', monospace;
      margin-bottom: 6px;
      text-transform: uppercase;
    }}
    .summary-text {{
      font-size: 10.5px;
      color: #888;
      line-height: 1.75;
    }}
    .quote-section {{
      position: relative;
      z-index: 1;
    }}
    .quote-label {{
      font-size: 8px;
      letter-spacing: 3px;
      color: #444;
      font-family: 'Courier New', monospace;
      margin-bottom: 6px;
      text-transform: uppercase;
    }}
    .quote-text {{
      font-size: 11px;
      color: #aaa;
      font-style: italic;
      line-height: 1.6;
    }}
    .quote-author {{
      font-size: 9px;
      color: #555;
      margin-top: 4px;
      letter-spacing: 1px;
    }}
    .deco-number {{
      position: absolute;
      right: 18px;
      bottom: 16px;
      font-size: 120px;
      font-weight: 900;
      color: {accent};
      opacity: .05;
      line-height: 1;
      pointer-events: none;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="top-stripe"></div>
    <div class="glow"></div>
    
    <div class="header">
      <div class="label">TODAY'S EDITION</div>
      <div class="title">세계경제<br/>뉴스</div>
      <div class="subtitle">WORLD ECONOMY BRIEFING</div>
    </div>
    
    <div class="summary-box">
      <div class="summary-label">TODAY'S SUMMARY</div>
      <div class="summary-text">{summary}</div>
    </div>
    
    <div class="quote-section">
      <div class="quote-label">💬 오늘의 명언</div>
      <div class="quote-text">"{quote['text']}"</div>
      <div class="quote-author">— {quote['author']}</div>
    </div>
    
    <div class="deco-number">6</div>
  </div>
</body>
</html>"""

def generate_html_news(card, date_str):
    """뉴스 카드 HTML 생성"""
    accent = card['accent']
    BG = "#08080F"
    CARD_BG = "#0D0D18"
    
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{card['headline']}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ 
      background: {BG}; 
      font-family: 'Georgia','Times New Roman',serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 20px;
    }}
    .card {{
      width: 340px;
      height: 340px;
      background: {CARD_BG};
      border-radius: 22px;
      padding: 22px;
      position: relative;
      overflow: hidden;
      border: 1px solid {accent}28;
      box-shadow: 0 0 0 1px {accent}28, 0 20px 70px rgba(0,0,0,.85), 0 0 50px {accent}18;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .top-stripe {{
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, transparent, {accent}, transparent);
    }}
    .glow {{
      position: absolute;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: radial-gradient(circle, {accent}1A 0%, transparent 70%);
      top: -60px;
      right: -60px;
      pointer-events: none;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      position: relative;
      z-index: 1;
      margin-bottom: 10px;
    }}
    .left-header {{
      flex: 1;
    }}
    .category {{
      font-size: 8px;
      letter-spacing: 3px;
      color: {accent};
      font-family: 'Courier New', monospace;
      margin-bottom: 5px;
      text-transform: uppercase;
    }}
    .emoji {{
      font-size: 36px;
    }}
    .number {{
      font-size: 52px;
      font-weight: 900;
      color: {accent};
      opacity: .1;
      line-height: 1;
      font-family: 'Courier New', monospace;
    }}
    .content {{
      position: relative;
      z-index: 1;
    }}
    .headline {{
      font-size: 29px;
      font-weight: 900;
      color: #fff;
      line-height: 1.15;
      white-space: pre-line;
      margin-bottom: 10px;
    }}
    .divider {{
      width: 28px;
      height: 2.5px;
      background: {accent};
      border-radius: 2px;
      margin-bottom: 10px;
    }}
    .body {{
      font-size: 11.5px;
      color: #9a9aaa;
      line-height: 1.75;
    }}
    .footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid #1a1a28;
      padding-top: 10px;
      margin-top: auto;
      position: relative;
      z-index: 1;
      font-size: 7.5px;
    }}
    .footer-left {{
      letter-spacing: 2.5px;
      color: #333;
      font-family: 'Courier New', monospace;
      text-transform: uppercase;
    }}
    .tag {{
      letter-spacing: 2px;
      color: {accent};
      background: {accent}12;
      padding: 3px 8px;
      border-radius: 20px;
      border: 1px solid {accent}28;
      font-family: 'Courier New', monospace;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="top-stripe"></div>
    <div class="glow"></div>
    
    <div class="header">
      <div class="left-header">
        <div class="category">{card['category']}</div>
        <div class="emoji">{card['emoji']}</div>
      </div>
      <div class="number">{card['num']}</div>
    </div>
    
    <div class="content">
      <div class="headline">{card['headline']}</div>
      <div class="divider"></div>
      <div class="body">{card['body']}</div>
    </div>
    
    <div class="footer">
      <span class="footer-left">ECONOMY NEWS · {date_str}</span>
      <span class="tag">#{card['tag']}</span>
    </div>
  </div>
</body>
</html>"""

def generate_images(output_dir, data):
    """HTML 파일을 생성하고 Puppeteer로 이미지 변환"""
    
    # HTML 파일 생성
    html_files = []
    
    # Cover HTML
    cover_html_path = os.path.join(output_dir, 'cover.html')
    with open(cover_html_path, 'w', encoding='utf-8') as f:
        f.write(generate_html_cover(data['date'], data['summary'], data['quote']))
    html_files.append((cover_html_path, '00-cover.png'))
    
    # News 카드 HTML들
    for i, card in enumerate(data['cards'][1:], 1):
        html_path = os.path.join(output_dir, f'card_{i}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(generate_html_news(card, data['date']))
        image_name = f"{str(i).zfill(2)}-{card['tag']}.png"
        html_files.append((html_path, image_name))
    
    # JavaScript 변환 스크립트 생성 (/tmp/react-converter에서 실행)
    convert_script = '/tmp/react-converter/convert-daily.js'
    
    # 파일 정보를 JSON으로 저장
    file_mapping = json.dumps([(h, os.path.join(output_dir, n)) for h, n in html_files])
    
    script_content = f"""const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const htmlMapping = {file_mapping};

async function convertToImages() {{
  const browser = await puppeteer.launch({{
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  }});
  
  try {{
    for (const [htmlFile, imagePath] of htmlMapping) {{
      const page = await browser.newPage();
      await page.setViewport({{ width: 400, height: 400, deviceScaleFactor: 2 }});
      
      await page.goto(`file://${{htmlFile}}`, {{ waitUntil: 'networkidle2' }});
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      await page.screenshot({{ path: imagePath, type: 'png' }});
      console.log(`✓ ${{imagePath}}`);
      await page.close();
    }}
    
    console.log('\\n✅ 모든 카드 변환 완료!');
    
  }} finally {{
    await browser.close();
  }}
}}

convertToImages().catch(err => {{
  console.error('변환 실패:', err);
  process.exit(1);
}});"""
    
    with open(convert_script, 'w') as f:
        f.write(script_content)
    
    # Node 스크립트 실행 (from /tmp/react-converter where puppeteer is installed)
    try:
        result = subprocess.run(
            ['node', convert_script],
            cwd='/tmp/react-converter',
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(result.stdout)
            
            # HTML 파일 삭제 (정리)
            for html_path, _ in html_files:
                try:
                    os.remove(html_path)
                except:
                    pass
            
            return True
        else:
            print(f"❌ 이미지 생성 실패:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 스크립트 실행 실패: {e}")
        return False

def generate_insta_caption(output_dir, data):
    """인스타그램 캡션 텍스트 파일 생성"""
    caption = f"""📰 세계경제 뉴스 {data['date']}

{data['summary']}

🔑 오늘의 주요 이슈

"""
    
    # 카드들 추가 (cover 제외)
    for card in data['cards'][1:]:
        caption += f"{card['emoji']} {card['headline'].replace(chr(10), ' ')}\n"
    
    caption += f"""
━━━━━━━━━━━━━━━
💬 오늘의 명언
"{data['quote']['text']}"
— {data['quote']['author']}

#세계경제 #경제뉴스 #주식 #환율 #유가 #코스피7000 #AI반도체 #글로벌경제 #카드뉴스 #매일경제
"""
    
    caption_path = os.path.join(output_dir, '인스타_캡션.txt')
    with open(caption_path, 'w', encoding='utf-8') as f:
        f.write(caption)
    
    print(f"✓ 인스타 캡션 저장: 인스타_캡션.txt")
    return caption_path

def is_weekday():
    """평일 여부 확인 (월~금)"""
    return datetime.now().weekday() < 5

def main():
    """메인 함수"""
    print(f"\n{'='*60}")
    print(f"🤖 세계경제 뉴스 카드 자동 생성 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 평일 확인
    if not is_weekday():
        print("⏸️  주말입니다. 작업 스킵")
        return
    
    # 뉴스 데이터 로드
    data = load_news_data()
    if not data:
        print("❌ 뉴스 데이터 없음. 종료합니다.")
        return
    
    # 폴더 생성
    output_dir, folder_name = get_date_folder()
    create_directory(output_dir)
    
    # JSX 파일 저장
    jsx_path = os.path.join(output_dir, 'economy-cards.jsx')
    with open(jsx_path, 'w', encoding='utf-8') as f:
        # JSX 파일 내용은 필요시 작성
        f.write("// React Component\n")
    
    print(f"📁 작업 폴더: {folder_name}")
    
    # 이미지 생성
    print(f"🎨 이미지 생성 중...\n")
    if generate_images(output_dir, data):
        print(f"\n✅ 완료!")
        print(f"📁 저장 위치: {output_dir}")
        
        # 인스타 캡션 생성
        generate_insta_caption(output_dir, data)
    else:
        print(f"\n❌ 이미지 생성 중 오류 발생")

if __name__ == "__main__":
    main()
