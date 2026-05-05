import React from 'react'

const LABELS = {
  hate_speech: {
    title: 'Үзэн ядалтын агуулга илэрсэн',
    description: 'Таны оруулсан текстэд үзэн ядалтын шинжтэй агуулга илэрлээ.',
  },
  harassment: {
    title: 'Дарамт, доромжлол илэрсэн',
    description: 'Таны оруулсан текстэд дарамт, доромжлолын шинжтэй агуулга илэрлээ.',
  },
  discrimination: {
    title: 'Ялгаварлан гадуурхалт илэрсэн',
    description: 'Таны оруулсан текстэд ялгаварлан гадуурхалтын шинжтэй агуулга илэрлээ.',
  },
  self_harm: {
    title: 'Тусламж хэрэгтэй юу?',
    description: 'Хэрэв та хүнд нөхцөл байдалд байгаа бол мэргэжлийн тусламж авна уу.',
  },
}

export default function SafetyWarning({ label }) {
  const info = LABELS[label] || { title: 'Анхааруулга', description: '' }

  return (
    <div className={`safety-warning safety-${label}`}>
      <div className="safety-icon">!</div>
      <div className="safety-text">
        <strong>{info.title}</strong>
        <p>{info.description}</p>
      </div>
    </div>
  )
}
