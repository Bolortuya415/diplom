import React, { useState, useRef, useEffect } from "react";
import { sendChat } from "../services/api";

const GREETING =
  "Сайн байна уу? Би танд хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хөгжлийн бэрхшээлтэй иргэдийн эрхийн талаар Монгол хуульд тулгуурласан зөвлөгөө өгөхөд бэлэн байна. Асуултаа бичнэ үү!";

const EXAMPLES = [
  "Хүйсийн тэгш эрх гэж юу вэ?",
  "Ялгаварлан гадуурхалтын эсрэг хууль Монголд байдаг уу?",
  "Хөгжлийн бэрхшээлтэй хүүхдийн боловсролын эрх юу вэ?",
];

export default function ChatWidget({ open, setOpen }) {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, loading]);

  const send = async (text) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput("");
    setMsgs((p) => [...p, { role: "user", content: q }]);
    setLoading(true);
    try {
      const d = await sendChat(q);
      setMsgs((p) => [...p, { role: "assistant", content: d.answer }]);
    } catch {
      setMsgs((p) => [
        ...p,
        {
          role: "assistant",
          content: "Уучлаарай, алдаа гарлаа. Дахин оролдоно уу.",
          err: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="cw-root">
      {open && (
        <div className="cw-panel">
          {/* Header */}
          <div className="cw-head">
            <div className="cw-brand">
              <div className="cw-avatar">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
                  <path
                    d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div>
                <div className="cw-name">Тэгшбот</div>
                <div className="cw-status">
                  <span className="cw-dot" />
                  Онлайн
                </div>
              </div>
            </div>
            <button
              className="cw-close"
              onClick={() => setOpen(false)}
              aria-label="Хаах"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
                <path
                  d="M18 6L6 18M6 6l12 12"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="cw-msgs">
            {msgs.length === 0 && (
              <>
                <div className="cw-msg assistant">
                  <p>{GREETING}</p>
                </div>
                <div className="cw-examples">
                  {EXAMPLES.map((q) => (
                    <button
                      key={q}
                      className="cw-example"
                      onClick={() => send(q)}
                      disabled={loading}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`cw-msg ${m.role}${m.err ? " err" : ""}`}>
                <p>{m.content}</p>
              </div>
            ))}
            {loading && (
              <div className="cw-msg assistant">
                <div className="typing-indicator">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div className="cw-composer">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder="Асуулт бичнэ үү..."
              rows={1}
              disabled={loading}
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="cw-send"
              aria-label="Илгээх"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
                <path
                  d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Floating action button */}
      <button
        className={`cw-fab${open ? " is-open" : ""}`}
        onClick={() => setOpen(!open)}
        aria-label="Чат нээх/хаах"
      >
        {open ? (
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
            <path
              d="M18 6L6 18M6 6l12 12"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        ) : (
          <>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
              <path
                d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>Зөвлөгөө авах</span>
          </>
        )}
      </button>
    </div>
  );
}
