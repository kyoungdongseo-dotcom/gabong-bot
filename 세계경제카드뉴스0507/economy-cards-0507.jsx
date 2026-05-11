import { useState } from "react";

const DATE = "2026년 5월 7일";

const cards = [
  {
    type: "cover",
    date: DATE,
  },
  {
    num: "01",
    emoji: "🕊️",
    category: "외교 · 에너지",
    headline: "미·이란\n종전 급물살",
    body: "미국-이란 휴전 합의가 속도를 내며 시장은 사실상 전쟁 마무리 수순으로 받아들이는 분위기. 국제유가 급락, 글로벌 증시 최고치 랠리 지속.",
    tag: "CEASEFIRE",
    accent: "#38BDF8",
  },
  {
    num: "02",
    emoji: "🛢️",
    category: "에너지 · 중동",
    headline: "사우디 유가\n인하 고육책",
    body: "사우디, 아시아향 6월 인도분 원유 배럴당 4달러 인하. 그러나 호르무즈 봉쇄로 송유관 우회 비용 급등, 국내 기름값 상승세는 꺾기 역부족.",
    tag: "OIL_MARKET",
    accent: "#F59E0B",
  },
  {
    num: "03",
    emoji: "📈",
    category: "증시 · 반도체",
    headline: "코스피 7000\n시대 개막",
    body: "코스피 7000선 돌파로 국내 증시 역사 새로 쓰다. AMD 호실적에 힘입어 반도체주 강세 지속, 글로벌 AI 투자 수요 증가가 핵심 동력.",
    tag: "KOSPI_7000",
    accent: "#10B981",
  },
  {
    num: "04",
    emoji: "💴",
    category: "환율 · 외환",
    headline: "엔화 1%\n강세 전환",
    body: "미·이란 휴전 기대감과 일본 당국 개입 관측이 맞물리며 달러 대비 엔화 1% 강세. 안전자산 선호 심리 완화 신호로 해석.",
    tag: "FX_MARKET",
    accent: "#8B5CF6",
  },
  {
    num: "05",
    emoji: "🤖",
    category: "AI · 빅테크",
    headline: "AMD 호실적\nAI 랠리 견인",
    body: "AMD가 시장 예상을 웃도는 1분기 실적 발표. AI 반도체 수요 폭증이 실적 견인, 엔비디아·TSMC 등 관련주 동반 상승.",
    tag: "AI_CHIPS",
    accent: "#EF4444",
  },
  {
    num: "06",
    emoji: "🛍️",
    category: "유통 · 소비",
    headline: "쿠팡 결제\n완전 회복",
    body: "작년 개인정보 유출 사태 후 일시 감소했던 쿠팡 카드 결제액이 4월 4조 6천억원으로 완전 회복. 소비자 신뢰 빠르게 복귀.",
    tag: "ECOMMERCE",
    accent: "#F97316",
  },
];

const QUOTE = {
  text: "위기는 위험과 기회가 함께 오는 순간이다.",
  author: "존 F. 케네디",
};

const SUMMARY =
  "미·이란 종전 합의가 급물살을 타며 오늘 시장 분위기는 완전히 뒤바뀌었습니다. 유가가 급락하고 코스피는 7000선을 돌파하며 새 역사를 썼지만, 호르무즈 봉쇄 여파로 기름값은 여전히 고공행진 중입니다. 지금 이 순간이 경제 패러다임의 전환점입니다.";

const BG = "#08080F";
const CARD_BG = "#0D0D18";

export default function App() {
  const [cur, setCur] = useState(0);
  const [fade, setFade] = useState(true);

  const total = cards.length;

  const go = (dir) => {
    setFade(false);
    setTimeout(() => {
      setCur((p) => (p + dir + total) % total);
      setFade(true);
    }, 110);
  };

  const dot = (i) => {
    setFade(false);
    setTimeout(() => { setCur(i); setFade(true); }, 110);
  };

  const card = cards[cur];
  const isCover = card.type === "cover";
  const accent = isCover ? "#38BDF8" : card.accent;

  return (
    <div style={{
      minHeight: "100vh", background: BG,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      fontFamily: "'Georgia','Times New Roman',serif",
      padding: "28px 16px", gap: 20,
      userSelect: "none",
    }}>

      {/* Header */}
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 10, letterSpacing: 5, color: "#333", fontFamily: "'Courier New',monospace" }}>
          WORLD ECONOMY · DAILY BRIEFING
        </div>
        <div style={{ fontSize: 13, color: "#555", marginTop: 4, letterSpacing: 2 }}>{DATE}</div>
      </div>

      {/* CARD */}
      <div style={{
        width: 340, height: 340, borderRadius: 22, position: "relative",
        overflow: "hidden", background: CARD_BG,
        boxShadow: `0 0 0 1px ${accent}28, 0 20px 70px rgba(0,0,0,.85), 0 0 50px ${accent}18`,
        opacity: fade ? 1 : 0,
        transform: fade ? "scale(1) translateY(0)" : "scale(.97) translateY(4px)",
        transition: "opacity .12s ease, transform .12s ease",
      }}>

        {/* Grid overlay */}
        <svg style={{ position:"absolute",inset:0,width:"100%",height:"100%",opacity:.035 }}>
          <defs>
            <pattern id="g" width="26" height="26" patternUnits="userSpaceOnUse">
              <path d="M 26 0 L 0 0 0 26" fill="none" stroke="white" strokeWidth=".5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#g)"/>
        </svg>

        {/* Glow */}
        <div style={{
          position:"absolute", width:260, height:260, borderRadius:"50%",
          background:`radial-gradient(circle,${accent}1A 0%,transparent 70%)`,
          top: isCover ? 20 : -60, right: isCover ? 20 : -60,
          pointerEvents:"none",
        }}/>

        {/* Top stripe */}
        <div style={{
          position:"absolute", top:0, left:0, right:0, height:3,
          background:`linear-gradient(90deg,transparent,${accent},transparent)`,
        }}/>

        {isCover ? (
          // ── COVER ──
          <div style={{ padding:"30px 28px", height:"100%", boxSizing:"border-box", display:"flex", flexDirection:"column", justifyContent:"space-between" }}>
            <div>
              <div style={{ fontSize:8, letterSpacing:4, color:accent, fontFamily:"'Courier New',monospace", marginBottom:14 }}>
                TODAY'S EDITION
              </div>
              <div style={{ fontSize:44, fontWeight:900, color:"#fff", lineHeight:1.0 }}>
                세계경제<br/>뉴스
              </div>
              <div style={{ fontSize:9, letterSpacing:5, color:"#222", fontFamily:"'Courier New',monospace", marginTop:8 }}>
                WORLD ECONOMY BRIEFING
              </div>
            </div>

            {/* Summary */}
            <div style={{
              background:"#ffffff08", borderRadius:10, padding:"12px 14px",
              border:`1px solid ${accent}22`,
            }}>
              <div style={{ fontSize:8, letterSpacing:3, color:accent, fontFamily:"'Courier New',monospace", marginBottom:6 }}>
                TODAY'S SUMMARY
              </div>
              <div style={{ fontSize:10.5, color:"#888", lineHeight:1.75 }}>
                {SUMMARY}
              </div>
            </div>

            {/* Quote */}
            <div>
              <div style={{ fontSize:8, letterSpacing:3, color:"#444", fontFamily:"'Courier New',monospace", marginBottom:6 }}>
                💬 오늘의 명언
              </div>
              <div style={{ fontSize:11, color:"#aaa", fontStyle:"italic", lineHeight:1.6 }}>
                "{QUOTE.text}"
              </div>
              <div style={{ fontSize:9, color:"#555", marginTop:4, letterSpacing:1 }}>
                — {QUOTE.author}
              </div>
            </div>

            {/* Big deco number */}
            <div style={{
              position:"absolute", right:18, bottom:16,
              fontSize:120, fontWeight:900, color:accent,
              opacity:.05, lineHeight:1, pointerEvents:"none",
            }}>6</div>
          </div>
        ) : (
          // ── NEWS CARD ──
          <div style={{ padding:"22px 22px 18px", height:"100%", boxSizing:"border-box", display:"flex", flexDirection:"column", justifyContent:"space-between" }}>

            {/* Top */}
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
              <div>
                <div style={{ fontSize:8, letterSpacing:3, color:accent, fontFamily:"'Courier New',monospace", marginBottom:5 }}>
                  {card.category}
                </div>
                <div style={{ fontSize:36 }}>{card.emoji}</div>
              </div>
              <div style={{ fontSize:52, fontWeight:900, color:accent, opacity:.1, lineHeight:1, fontFamily:"'Courier New',monospace" }}>
                {card.num}
              </div>
            </div>

            {/* Middle */}
            <div>
              <div style={{ fontSize:29, fontWeight:900, color:"#fff", lineHeight:1.15, whiteSpace:"pre-line", marginBottom:10 }}>
                {card.headline}
              </div>
              <div style={{ width:28, height:2.5, background:accent, borderRadius:2, marginBottom:10 }}/>
              <div style={{ fontSize:11.5, color:"#9a9aaa", lineHeight:1.75 }}>
                {card.body}
              </div>
            </div>

            {/* Footer */}
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", borderTop:"1px solid #1a1a28", paddingTop:10 }}>
              <span style={{ fontSize:7.5, letterSpacing:2.5, color:"#333", fontFamily:"'Courier New',monospace" }}>
                ECONOMY NEWS · {DATE}
              </span>
              <span style={{
                fontSize:7.5, letterSpacing:2, color:accent,
                background:`${accent}12`, padding:"3px 8px",
                borderRadius:20, border:`1px solid ${accent}28`,
                fontFamily:"'Courier New',monospace",
              }}>
                #{card.tag}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div style={{ display:"flex", alignItems:"center", gap:14 }}>
        <button onClick={() => go(-1)} style={{
          width:38, height:38, borderRadius:"50%",
          background:"#141420", border:"1px solid #2a2a3a",
          color:"#888", fontSize:16, cursor:"pointer",
          display:"flex", alignItems:"center", justifyContent:"center",
          transition:"all .15s",
        }}>‹</button>

        <div style={{ display:"flex", gap:5 }}>
          {cards.map((_, i) => (
            <div key={i} onClick={() => dot(i)} style={{
              width: cur === i ? 18 : 5, height:5, borderRadius:3,
              background: cur === i ? accent : "#252535",
              cursor:"pointer", transition:"all .25s ease",
            }}/>
          ))}
        </div>

        <button onClick={() => go(1)} style={{
          width:38, height:38, borderRadius:"50%",
          background:"#141420", border:"1px solid #2a2a3a",
          color:"#888", fontSize:16, cursor:"pointer",
          display:"flex", alignItems:"center", justifyContent:"center",
          transition:"all .15s",
        }}>›</button>
      </div>

      <div style={{ color:"#252535", fontSize:10, letterSpacing:3, fontFamily:"'Courier New',monospace" }}>
        {cur + 1} / {total}
      </div>

      {/* Instagram Caption Preview */}
      <div style={{
        width: 340, borderRadius:14, background:"#0D0D18",
        border:"1px solid #1a1a28", padding:"18px 18px",
        boxSizing:"border-box",
      }}>
        <div style={{ fontSize:9, letterSpacing:4, color:"#38BDF8", fontFamily:"'Courier New',monospace", marginBottom:12 }}>
          📋 인스타그램 캡션 복사용
        </div>
        <div style={{ fontSize:11, color:"#666", lineHeight:1.8, whiteSpace:"pre-line" }}>
{`📰 세계경제 뉴스 ${DATE}

${SUMMARY}

🔑 오늘의 주요 이슈
🕊️ 미·이란 종전 급물살
🛢️ 사우디 유가 인하 고육책
📈 코스피 7000 시대 개막
💴 엔화 1% 강세 전환
🤖 AMD 호실적 AI 랠리 견인
🛍️ 쿠팡 결제 완전 회복

━━━━━━━━━━━━━━━
💬 오늘의 명언
"${QUOTE.text}"
— ${QUOTE.author}

#세계경제 #경제뉴스 #주식 #환율 #유가 #코스피7000 #AI반도체 #글로벌경제 #카드뉴스 #매일경제`}
        </div>
      </div>

    </div>
  );
}
