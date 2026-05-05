import React, { useState, useRef, useEffect } from 'react'
import { sendChat, submitFeedback } from '../services/api'
import MessageBubble from '../components/MessageBubble'
import SourcePanel from '../components/SourcePanel'
import SafetyWarning from '../components/SafetyWarning'

const CATEGORY_META = {
  gender_equality: {
    title: 'Хүйсийн тэгш эрх',
    className: 'cat-gender',
    greeting:
      'Сайн байна уу! Би хүйсийн тэгш эрхийн талаар мэдээлэл, зөвлөгөө өгөх туслах юм. Хүйсийн тэгш байдлын хууль, ажлын байрны тэгш боломж, бэлгийн дарамт, гэр бүлийн харилцаа зэрэг сэдвээр асууж болно.',
    examples: [
      { tag: 'Хууль', text: 'Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?' },
      { tag: 'Ажлын байр', text: 'Ажлын байранд бэлгийн дарамтаас хэрхэн хамгаалах вэ?' },
      { tag: 'Гэр бүл', text: 'Хүйсийн тэгш байдал гэр бүлд ямар ач холбогдолтой вэ?' },
    ],
  },
  discrimination: {
    title: 'Ялгаварлан гадуурхалт',
    className: 'cat-discrimination',
    greeting:
      'Сайн байна уу! Би ялгаварлан гадуурхалтын эсрэг мэдээлэл, зөвлөгөө өгөх туслах юм. Ялгаварлан гадуурхалтын хэлбэрүүд, хуулийн хамгаалалт, гомдол гаргах журам, сургуулийн дарамт зэрэг сэдвээр асууж болно.',
    examples: [
      { tag: 'Хууль', text: 'Ялгаварлан гадуурхалтын эсрэг хууль Монголд байдаг уу?' },
      { tag: 'Сургууль', text: 'Сургуулийн дарамтад өртсөн үед хаана хандах вэ?' },
      { tag: 'Гомдол', text: 'Ажил олгогч ялгаварлан гадуурхвал хаана гомдол гаргах вэ?' },
    ],
  },
  disability: {
    title: 'Хөгжлийн бэрхшээлтэй иргэн',
    className: 'cat-disability',
    greeting:
      'Сайн байна уу! Би хөгжлийн бэрхшээлтэй иргэдийн эрхийн талаар мэдээлэл, зөвлөгөө өгөх туслах юм. Хууль эрх зүй, боловсрол, ажил эрхлэлт, нийгмийн хамгаалал, хүртээмжтэй орчин зэрэг сэдвээр асууж болно.',
    examples: [
      { tag: 'Хууль', text: 'Хөгжлийн бэрхшээлтэй хүмүүсийн эрхийн тухай хууль юу вэ?' },
      { tag: 'Боловсрол', text: 'Хөгжлийн бэрхшээлтэй хүүхдийн боловсролын эрх юу вэ?' },
      { tag: 'Ажил', text: 'Хөгжлийн бэрхшээлтэй хүн ажилд орох эрхийг хэн хамгаалдаг вэ?' },
    ],
  },
}

export default function ChatPage({ category, onBack }) {
  const meta = CATEGORY_META[category] || CATEGORY_META.gender_equality
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedSources, setSelectedSources] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const query = input.trim()
    if (!query || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setLoading(true)

    try {
      const data = await sendChat(query, category)
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources,
          safety: data.safety,
          chatId: data.chat_id,
          responseTime: data.response_time_ms,
          feedbackGiven: null,
        },
      ])
    } catch (err) {
      const errorMsg = err.message && !err.message.startsWith('Chat failed:')
        ? err.message
        : 'Уучлаарай, алдаа гарлаа. Дахин оролдоно уу.'
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: errorMsg,
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (msgIndex, rating) => {
    const msg = messages[msgIndex]
    if (!msg.chatId || msg.feedbackGiven !== null) return

    try {
      await submitFeedback(msg.chatId, rating)
      setMessages(prev => {
        const updated = [...prev]
        updated[msgIndex] = { ...updated[msgIndex], feedbackGiven: rating }
        return updated
      })
    } catch (err) {
      console.error('Feedback error:', err)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-container">
        <div className="chat-topic-header">
          <button className="back-btn" onClick={onBack}>
            ← Буцах
          </button>
          <span className={`chat-topic-badge ${meta.className}`}>
            {meta.title}
          </span>
        </div>

        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <span className="welcome-chip">Тэгшбот • {meta.title}</span>
              <h2>{meta.title}</h2>
              <p>{meta.greeting}</p>
              <div className="example-questions">
                <p className="example-label">Санал болгох асуултууд</p>
                <div className="example-grid">
                  {meta.examples.map((q) => (
                    <button
                      key={q.text}
                      className="example-card"
                      onClick={() => setInput(q.text)}
                    >
                      <span className="example-tag">{q.tag}</span>
                      <span className="example-text">{q.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <React.Fragment key={i}>
              {msg.safety && !msg.safety.is_safe && (
                <SafetyWarning label={msg.safety.label} />
              )}
              <MessageBubble
                message={msg}
                onFeedback={(rating) => handleFeedback(i, rating)}
                onShowSources={() => setSelectedSources(msg.sources)}
              />
            </React.Fragment>
          ))}

          {loading && (
            <div className="message assistant loading">
              <div className="typing-indicator" aria-label="Хариулт бэлтгэж байна">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <div className="input-wrap">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`${meta.title}-ийн талаар асуух...`}
              rows={1}
              disabled={loading}
            />
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={loading || !input.trim()}
              aria-label="Илгээх"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
                <path
                  d="M4 12l16-8-6 18-3-7-7-3z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              </svg>
              <span>Илгээх</span>
            </button>
          </div>
          <p className="input-hint">
            Enter — илгээх · Shift + Enter — шинэ мөр · Хариултууд нь эх сурвалжид тулгуурласан болно
          </p>
        </div>
      </div>

      {selectedSources && (
        <SourcePanel
          sources={selectedSources}
          onClose={() => setSelectedSources(null)}
        />
      )}
    </div>
  )
}
