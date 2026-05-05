import React from 'react'

const CATEGORIES = [
  {
    id: 'gender_equality',
    className: 'cat-gender',
    icon: '⚖️',
    title: 'Хүйсийн тэгш эрх',
    description:
      'Хүйсийн тэгш байдал, эмэгтэйчүүдийн эрх, жендэрийн бодлого, ажлын байрны тэгш боломж, гэр бүлийн харилцаанд хүйсийн тэнцвэрт байдлын талаар мэдээлэл аваарай.',
    examples: [
      'Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?',
      'Ажлын байранд бэлгийн дарамтаас хэрхэн хамгаалах вэ?',
    ],
  },
  {
    id: 'discrimination',
    className: 'cat-discrimination',
    icon: '🛡️',
    title: 'Ялгаварлан гадуурхалт',
    description:
      'Ялгаварлан гадуурхалтын хэлбэрүүд, хуулийн хамгаалалт, гомдол гаргах журам, сургуулийн дарамт, үзэн ядалтын яриа, тэгш эрхийн зөрчлийн талаар зөвлөгөө аваарай.',
    examples: [
      'Ялгаварлан гадуурхалтын эсрэг хууль Монголд байдаг уу?',
      'Сургуулийн дарамтад өртсөн үед хаана хандах вэ?',
    ],
  },
  {
    id: 'disability',
    className: 'cat-disability',
    icon: '♿',
    title: 'Хөгжлийн бэрхшээлтэй иргэн',
    description:
      'Хөгжлийн бэрхшээлтэй иргэдийн эрх, боловсролын хүртээмж, ажил эрхлэлт, нийгмийн хамгаалал, хүртээмжтэй орчин бүрдүүлэх талаар мэдээлэл аваарай.',
    examples: [
      'Хөгжлийн бэрхшээлтэй хүмүүсийн эрхийн тухай хууль юу вэ?',
      'Хөгжлийн бэрхшээлтэй хүүхдийн боловсролын эрх юу вэ?',
    ],
  },
]

export default function LandingPage({ onSelectCategory }) {
  return (
    <div className="landing-page">
      <div className="landing-hero">
        <span className="landing-hero-badge">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none">
            <path
              d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Тэгшбот • AI Зөвлөгөө
        </span>
        <h1>Тэгш эрх, хүртээмжтэй нийгмийн төлөө</h1>
        <p>
          Хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хөгжлийн бэрхшээлтэй иргэдийн
          эрхийн талаар Монгол хэл дээр мэдээлэл, зөвлөгөө авах боломжтой ухаалаг
          туслах чатбот.
        </p>
      </div>

      <div className="landing-categories">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            className={`category-card ${cat.className}`}
            onClick={() => onSelectCategory(cat.id)}
          >
            <div className="category-icon">{cat.icon}</div>
            <h2>{cat.title}</h2>
            <p>{cat.description}</p>
            <span className="category-arrow">
              Зөвлөгөө авах →
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

export { CATEGORIES }
