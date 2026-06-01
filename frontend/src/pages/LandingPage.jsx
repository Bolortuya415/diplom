import React from "react";

const STATS = [
  {
    num: "3",
    unit: "үндсэн сэдэв",
    desc: "Хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хөгжлийн бэрхшээлтэй иргэдийн эрх",
  },
  {
    num: "100%",
    unit: "эх сурвалжтай хариулт",
    desc: "Монголын хууль, эрх зүйн мэдээлэлд тулгуурласан",
  },
  {
    num: "24/7",
    unit: "нээлттэй",
    desc: "Хэзээ ч, хаанаас ч мэдээлэл авах боломжтой",
  },
];

const INFO = [
  {
    color: "#0d9488",
    border: "#ccfbf1",
    iconBg: "#f0fdfa",
    Icon: () => (
      <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
        <rect
          x="22"
          y="6"
          width="4"
          height="30"
          rx="2"
          fill="#0d9488"
          opacity="0.8"
        />
        <rect x="6" y="12" width="36" height="4" rx="2" fill="#0d9488" />
        <line
          x1="12"
          y1="16"
          x2="12"
          y2="26"
          stroke="#0d9488"
          strokeWidth="2.5"
        />
        <ellipse
          cx="12"
          cy="29"
          rx="9"
          ry="3.5"
          stroke="#0d9488"
          strokeWidth="2"
          fill="none"
        />
        <line
          x1="36"
          y1="16"
          x2="36"
          y2="26"
          stroke="#0d9488"
          strokeWidth="2.5"
        />
        <ellipse
          cx="36"
          cy="29"
          rx="9"
          ry="3.5"
          stroke="#0d9488"
          strokeWidth="2"
          fill="none"
        />
        <circle cx="24" cy="11" r="4" fill="#0d9488" opacity="0.5" />
      </svg>
    ),
    title: "Хүйсийн тэгш эрх",
    body: "Хүйсийн тэгш эрх гэдэг нь эмэгтэй, эрэгтэй болон хүн бүр хүйсээсээ үл хамааран сурч боловсрох, ажиллах, шийдвэр гаргах, нийгмийн амьдралд оролцох тэгш боломжтой байхыг хэлнэ. Тэгш эрхтэй орчин бүрдсэнээр хүн өөрийн боломжоо бүрэн ашиглаж, сурч хөгжих, ажиллах, нийгэмд идэвхтэй оролцох нөхцөл бүрддэг.",
    bullets: [
      "Ажилд орох, албан тушаал ахих, цалин хөлс авахад хүйсээр ялгаварлах ёсгүй",
      "Шийдвэр гаргах түвшинд хүн бүр тэгш оролцох боломжтой байх ёстой",
      "Жирэмсэн, хүүхэд асарч байгаа, гэр бүлийн байдал зэргээр ажил, сургууль дээр дарамт үзүүлэх нь зохисгүй",
      "Бэлгийн болон сэтгэл санааны дарамтаас хамгаалуулах эрхтэй",
    ],
  },
  {
    color: "#0ea5e9",
    border: "#bae6fd",
    iconBg: "#f0f9ff",
    Icon: () => (
      <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
        <path
          d="M24 6L8 12v14c0 9 7 16 16 18 9-2 16-9 16-18V12L24 6z"
          stroke="#0ea5e9"
          strokeWidth="2.5"
          fill="#e0f2fe"
        />
        <path
          d="M17 24l5 5 9-9"
          stroke="#0ea5e9"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
    title: "Ялгаварлан гадуурхалтын эсрэг",
    body: "Ялгаварлан гадуурхалт гэдэг нь хүнийг арьс өнгө, хүйс, нас, хөгжлийн бэрхшээл, шашин шүтлэг, үзэл бодол, нийгмийн гарал, боловсрол, эдийн засгийн байдал зэрэг шинжээр нь бусдаас дорд үзэх, боломжийг нь хязгаарлах үйлдэл юм.",
    bullets: [
      "Ажил, сургууль, үйлчилгээ авах үед хүн бүр тэгш хандлага хүртэх эрхтэй",
      "Доромжилсон үг хэллэг, дээрэлхэлт, гадуурхалт нь эрхийн зөрчил байж болно",
      "Цахим орчин дахь дарамт, гутаан доромжлолыг ч мөн зөрчил гэж үзэж болно",
      "Зөрчил гарвал байгууллагын удирдлага, хүний эрхийн байгууллага, холбогдох хуулийн байгууллагад хандаж болно",
    ],
  },
  {
    color: "#7c3aed",
    border: "#ddd6fe",
    iconBg: "#f5f3ff",
    Icon: () => (
      <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
        <circle
          cx="24"
          cy="11"
          r="6"
          stroke="#7c3aed"
          strokeWidth="2.5"
          fill="none"
        />
        <path
          d="M24 18v12"
          stroke="#7c3aed"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <path
          d="M15 24h18"
          stroke="#7c3aed"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <path
          d="M19 30l-4 10M29 30l4 10"
          stroke="#7c3aed"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
    ),
    title: "Хөгжлийн бэрхшээлтэй иргэдийн эрх",
    body: "Хүртээмжтэй орчин, тэгш боловсрол, хөдөлмөр эрхлэлт, эрүүл мэндийн үйлчилгээ, нийгмийн хамгаалал нь хөгжлийн бэрхшээлтэй иргэдийн эрхийг хангах чухал хэсэг юм.",
    bullets: [
      "Сургууль, ажлын байр, төрийн болон хувийн үйлчилгээ хүртээмжтэй байх ёстой",
      "Мэдээлэл, барилга байгууламж, цахим үйлчилгээ хүн бүрт ойлгомжтой, ашиглах боломжтой байх шаардлагатай",
      "Хөгжлийн бэрхшээлээр нь ялгаварлах, боломжийг нь хязгаарлах нь эрхийн зөрчил байж болно",
      "Тусламж, дэмжлэг, нөхөн сэргээх үйлчилгээ, нийгмийн хамгаалалд хамрагдах эрхтэй",
    ],
  },
];

const STEPS = [
  {
    num: "01",
    title: "Чатаа нээнэ",
    desc: "Доорх “Зөвлөгөө авах” товчийг дарж чат цонхыг нээнэ.",
    icon: (
      <svg viewBox="0 0 32 32" width="28" height="28" fill="none">
        <rect
          x="4"
          y="6"
          width="24"
          height="20"
          rx="3"
          stroke="currentColor"
          strokeWidth="2"
        />
        <path
          d="M10 13h12M10 17h8"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    num: "02",
    title: "Асуултаа бичнэ",
    desc: "Өөрийн нөхцөл байдалтай холбоотой асуултаа Монгол хэлээр бичнэ.",
    icon: (
      <svg viewBox="0 0 32 32" width="28" height="28" fill="none">
        <path
          d="M16 4L4 10l12 6 12-6-12-6zM4 22l12 6 12-6M4 16l12 6 12-6"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    num: "03",
    title: "Хариулт хүлээн авна",
    desc: "Эх сурвалжид тулгуурласан хариулт болон зөвлөгөөг авна.",
    icon: (
      <svg viewBox="0 0 32 32" width="28" height="28" fill="none">
        <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="2" />
        <path
          d="M11 16l4 4 6-7"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
];

export default function LandingPage({ onOpenChat }) {
  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="landing">
      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="lp-hero">
        <div className="lp-hero-inner">
          <div className="lp-hero-text">
            <span className="lp-hero-tag">Хууль зүйн туслах</span>
            <h1>
              Тэгш эрхийнхээ талаар мэд.
              <br />
              Өөрийгөө хамгаал.
            </h1>
            <p>
              Хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хөгжлийн бэрхшээлтэй
              иргэдийн эрхийн талаар Монголын хуульд тулгуурласан мэдээлэл,
              зөвлөгөөг энгийн ойлгомжтой хэлбэрээр аваарай.
            </p>
            <div className="lp-hero-actions">
              <button className="btn-primary-lg" onClick={onOpenChat}>
                Зөвлөгөө авах
                <svg viewBox="0 0 20 20" width="16" height="16" fill="none">
                  <path
                    d="M4 10h12M11 6l4 4-4 4"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <button
                className="btn-ghost-lg"
                onClick={() => scrollTo("about")}
              >
                Дэлгэрэнгүй мэдэх
              </button>
            </div>
            <div className="lp-hero-trust">
              <span>
                <svg viewBox="0 0 16 16" width="13" height="13" fill="none">
                  <path
                    d="M8 2L2 5v5c0 3.5 2.5 6.5 6 7.5 3.5-1 6-4 6-7.5V5L8 2z"
                    fill="currentColor"
                    opacity="0.7"
                  />
                </svg>
                Монголын үндсэн хууль
              </span>
              <span>
                <svg viewBox="0 0 16 16" width="13" height="13" fill="none">
                  <circle
                    cx="8"
                    cy="8"
                    r="6"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    opacity="0.7"
                  />
                  <path
                    d="M5 8l2 2 4-4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    opacity="0.7"
                  />
                </svg>
                Эх сурвалжтай хариулт
              </span>
              <span>
                <svg viewBox="0 0 16 16" width="13" height="13" fill="none">
                  <rect
                    x="2"
                    y="2"
                    width="12"
                    height="12"
                    rx="2"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    opacity="0.7"
                  />
                  <path
                    d="M5 8h6M5 5h6M5 11h4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    opacity="0.7"
                  />
                </svg>
                Монгол хэл дээр
              </span>
            </div>
          </div>

          {/* Hero illustration */}
          <div className="lp-hero-visual" aria-hidden="true">
            <svg
              viewBox="0 0 360 300"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="lp-hero-svg"
            >
              {/* Outer ring */}
              <circle
                cx="180"
                cy="150"
                r="130"
                stroke="rgba(255,255,255,0.08)"
                strokeWidth="1"
                strokeDasharray="5 7"
              />
              <circle
                cx="180"
                cy="150"
                r="90"
                stroke="rgba(255,255,255,0.06)"
                strokeWidth="1"
              />
              {/* Scale pole */}
              <rect
                x="178"
                y="60"
                width="4"
                height="110"
                rx="2"
                fill="rgba(255,255,255,0.5)"
              />
              {/* Scale beam */}
              <path
                d="M90 110 Q180 98 270 110"
                stroke="rgba(255,255,255,0.75)"
                strokeWidth="3"
                strokeLinecap="round"
                fill="none"
              />
              {/* Pivot */}
              <circle cx="180" cy="103" r="7" fill="rgba(255,255,255,0.8)" />
              {/* Left string + pan */}
              <line
                x1="100"
                y1="110"
                x2="100"
                y2="148"
                stroke="rgba(255,255,255,0.45)"
                strokeWidth="2"
              />
              <path
                d="M74 150 Q100 162 126 150"
                stroke="rgba(255,255,255,0.7)"
                strokeWidth="2.5"
                strokeLinecap="round"
                fill="rgba(255,255,255,0.08)"
              />
              {/* Right string + pan */}
              <line
                x1="262"
                y1="110"
                x2="262"
                y2="148"
                stroke="rgba(255,255,255,0.45)"
                strokeWidth="2"
              />
              <path
                d="M236 150 Q262 162 288 150"
                stroke="rgba(255,255,255,0.7)"
                strokeWidth="2.5"
                strokeLinecap="round"
                fill="rgba(255,255,255,0.08)"
              />
              {/* Left figure */}
              <circle cx="90" cy="140" r="10" fill="rgba(255,255,255,0.85)" />
              <path
                d="M78 158 Q90 170 102 158"
                fill="rgba(255,255,255,0.65)"
                stroke="none"
              />
              {/* Right figure */}
              <circle cx="272" cy="140" r="10" fill="rgba(255,255,255,0.85)" />
              <rect
                x="263"
                y="152"
                width="18"
                height="14"
                rx="2"
                fill="rgba(255,255,255,0.65)"
              />
              {/* Center figure (disability) */}
              <circle cx="180" cy="192" r="8" fill="rgba(255,255,255,0.7)" />
              <path
                d="M172 200 Q180 214 188 200"
                fill="rgba(255,255,255,0.5)"
              />
              <circle
                cx="192"
                cy="215"
                r="6"
                stroke="rgba(255,255,255,0.6)"
                strokeWidth="2"
                fill="none"
              />
              {/* Equal sign */}
              <rect
                x="157"
                y="236"
                width="46"
                height="5"
                rx="2.5"
                fill="rgba(255,255,255,0.55)"
              />
              <rect
                x="157"
                y="248"
                width="46"
                height="5"
                rx="2.5"
                fill="rgba(255,255,255,0.55)"
              />
              {/* Sparkles */}
              <circle cx="140" cy="72" r="3" fill="rgba(255,255,255,0.5)" />
              <circle cx="222" cy="68" r="2.5" fill="rgba(255,255,255,0.45)" />
              <circle cx="116" cy="88" r="2" fill="rgba(255,255,255,0.35)" />
              <circle cx="248" cy="85" r="2.5" fill="rgba(255,255,255,0.4)" />
              <circle cx="310" cy="130" r="3" fill="rgba(255,255,255,0.3)" />
              <circle cx="52" cy="125" r="2" fill="rgba(255,255,255,0.3)" />
            </svg>
          </div>
        </div>
      </section>

      {/* ── Stats strip ────────────────────────────────────────── */}
      <section className="lp-stats">
        {STATS.map((s) => (
          <div key={s.num} className="lp-stat">
            <div className="lp-stat-num">
              {s.num}
              <span className="lp-stat-unit">{s.unit}</span>
            </div>
            <div className="lp-stat-desc">{s.desc}</div>
          </div>
        ))}
      </section>

      {/* ── Why it matters ─────────────────────────────────────── */}
      <section className="lp-about" id="about">
        <div className="lp-section-head">
          <h2>Яагаад мэдлэг чухал вэ?</h2>
          <p>
            Монгол Улс тэгш эрхийг хангах олон хуультай боловч иргэд мэдлэг
            дутмагаас болж өөрийн эрхийг бүрэн эдлэж чаддаггүй.
          </p>
        </div>
        <div className="lp-info-grid">
          {INFO.map((item) => (
            <div
              key={item.title}
              className="lp-info-card"
              style={{
                "--ic": item.color,
                "--ib": item.border,
                "--ibg": item.iconBg,
              }}
            >
              <div className="lp-info-icon-wrap">
                <item.Icon />
              </div>
              <h3>{item.title}</h3>
              <p className="lp-info-body">{item.body}</p>
              <ul className="lp-info-bullets">
                {item.bullets.map((b) => (
                  <li key={b}>
                    <svg
                      viewBox="0 0 16 16"
                      width="12"
                      height="12"
                      fill="none"
                      aria-hidden="true"
                    >
                      <circle
                        cx="8"
                        cy="8"
                        r="7"
                        fill="var(--ic)"
                        opacity="0.15"
                      />
                      <path
                        d="M5 8l2 2 4-4"
                        stroke="var(--ic)"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                      />
                    </svg>
                    {b}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ───────────────────────────────────────── */}
      <section className="lp-how" id="how-it-works">
        <div className="lp-section-head light">
          <h2>Хэрхэн ажиллах вэ?</h2>
          <p>Гурван энгийн алхамаар мэдэхийг хүссэн мэдлэгээ олж авна.</p>
        </div>
        <div className="lp-steps">
          {STEPS.map((s, idx) => (
            <div key={s.num} className="lp-step">
              <div className="lp-step-num">{s.num}</div>
              <div className="lp-step-icon">{s.icon}</div>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
              {idx < STEPS.length - 1 && (
                <div className="lp-step-arrow" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
                    <path
                      d="M9 18l6-6-6-6"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ──────────────────────────────────────────── */}
      <section className="lp-final-cta" id="start">
        <div className="lp-section-head">
          <h2>Асуултаа бичихэд бэлэн үү?</h2>
          <p>
            AI Чатбот-оос дээрх сэдвийн хүрээнд Монголын хууль, эх сурвалжид
            тулгуурласан хариулт аваарай.
          </p>
        </div>
        <div className="lp-cta-actions">
          <button className="btn-primary-lg" onClick={onOpenChat}>
            Чат эхлэх
            <svg viewBox="0 0 20 20" width="16" height="16" fill="none">
              <path
                d="M4 10h12M11 6l4 4-4 4"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </section>

      {/* ── Disclaimer ─────────────────────────────────────────── */}
      <section className="lp-disclaimer">
        <svg
          viewBox="0 0 20 20"
          width="16"
          height="16"
          fill="none"
          aria-hidden="true"
        >
          <circle
            cx="10"
            cy="10"
            r="9"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <path
            d="M10 6v5M10 14v.5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
        <p>
          Тэгшбот нь Монгол Улсын хуулийн баримт бичигт тулгуурлан мэдээлэл
          өгдөг бөгөөд мэргэшсэн хуулийн зөвлөгөөг орлохгүй болно. Тодорхой
          хуулийн тусламж шаардлагатай бол өмгөөлөгч эсвэл холбогдох
          байгууллагад хандана уу.
        </p>
      </section>
    </div>
  );
}
