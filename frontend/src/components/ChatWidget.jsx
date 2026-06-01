import React, { useState, useRef, useEffect, useMemo } from "react";
import { sendChat, submitFeedback } from "../services/api";

const GREETING =
  "Сайн байна уу? Би танд хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хөгжлийн бэрхшээлтэй иргэдийн эрхийн талаар Монгол хуульд тулгуурласан зөвлөгөө өгөхөд бэлэн байна. Асуултаа бичнэ үү!";

const EXAMPLES = [
  "Хүйсийн тэгш эрх гэж юу вэ?",
  "Ялгаварлан гадуурхалтын эсрэг хууль Монголд байдаг уу?",
  "Хөгжлийн бэрхшээлтэй хүүхдийн боловсролын эрх юу вэ?",
];

// How long to wait after the bot's response with no further user message
// before showing the rating prompt. 20 s is a comfortable window — long
// enough that follow-up questions don't get interrupted, short enough that
// the prompt still feels related to the answer the user just read.
const INACTIVITY_MS = 20000;

const FEEDBACK_PROMPT_TEXT =
  "Танд өөр асуулт байгаа юу? Хэрэв байхгүй бол миний хариултыг 1-5 оноогоор үнэлнэ үү.";
const FEEDBACK_THANKS_TEXT = "Үнэлгээ илгээсэнд баярлалаа.";

// Stable session ID for the whole widget lifetime — sent with every
// feedback submission so the analyst can group ratings by conversation.
const newSessionId = () => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `s-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

export default function ChatWidget({ open, setOpen }) {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedSrc, setExpandedSrc] = useState(new Set());
  const endRef = useRef(null);

  // Session ID — stable for the lifetime of the widget component.
  const sessionId = useMemo(() => newSessionId(), []);

  // Inactivity-prompt machinery.
  // promptedChatIds: chat IDs we have already shown a prompt for (so we
  // never ask twice for the same bot answer, even after re-renders).
  const promptedChatIds = useRef(new Set());
  // ratedChatIds: chat IDs the user has already rated.
  const ratedChatIds = useRef(new Set());
  const inactivityTimer = useRef(null);

  const clearInactivityTimer = () => {
    if (inactivityTimer.current) {
      clearTimeout(inactivityTimer.current);
      inactivityTimer.current = null;
    }
  };

  // Remove any *pending* (not yet rated) feedback prompt from the visible
  // message stream. Submitted prompts stay so the user keeps seeing the
  // "Thank you" confirmation.
  const removePendingPrompt = () => {
    setMsgs((p) =>
      p.filter(
        (m) =>
          !(
            m.role === "system" &&
            m.kind === "feedback-prompt" &&
            m.status === "pending"
          ),
      ),
    );
  };

  const startInactivityTimer = (forChatId) => {
    clearInactivityTimer();
    if (forChatId == null) return;
    if (promptedChatIds.current.has(forChatId)) return;
    if (ratedChatIds.current.has(forChatId)) return;

    inactivityTimer.current = setTimeout(() => {
      // Double-check at fire time — guards against races where another
      // prompt was already injected or the user already rated.
      if (promptedChatIds.current.has(forChatId)) return;
      if (ratedChatIds.current.has(forChatId)) return;
      promptedChatIds.current.add(forChatId);
      setMsgs((p) => [
        ...p,
        {
          role: "system",
          kind: "feedback-prompt",
          targetChatId: forChatId,
          status: "pending",
        },
      ]);
    }, INACTIVITY_MS);
  };

  // Clean up the timer when the component unmounts or when the widget is
  // closed (we don't want a stale prompt to pop up after re-open).
  useEffect(() => {
    return () => clearInactivityTimer();
  }, []);

  useEffect(() => {
    if (!open) {
      clearInactivityTimer();
    }
  }, [open]);

  const toggleSourceExpanded = (key) => {
    setExpandedSrc((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, loading]);

  const send = async (text) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;

    // Sending a new message cancels any pending inactivity prompt.
    clearInactivityTimer();
    removePendingPrompt();

    setInput("");
    setMsgs((p) => [...p, { role: "user", content: q }]);
    setLoading(true);
    let respChatId = null;
    try {
      const history = msgs
        .filter(
          (m) =>
            !m.err &&
            m.content &&
            (m.role === "user" || m.role === "assistant"),
        )
        .slice(-8)
        .map((m) => ({ role: m.role, content: m.content }));
      const d = await sendChat(q, history);
      respChatId = d.chat_id ?? null;
      setMsgs((p) => [
        ...p,
        {
          role: "assistant",
          content: d.answer,
          chatId: d.chat_id,
          sources: d.sources || [],
        },
      ]);
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
      // Only arm the prompt for successful, identifiable bot responses.
      if (respChatId != null) {
        startInactivityTimer(respChatId);
      }
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  // Submit the 1-5 rating attached to a specific feedback-prompt message.
  // After success we mark the prompt as "submitted" and record the chatId
  // so we never re-prompt for the same answer.
  const submitRating = async (promptIdx, chatId, rating) => {
    setMsgs((p) =>
      p.map((m, i) =>
        i === promptIdx ? { ...m, status: "submitting", rating } : m,
      ),
    );
    try {
      await submitFeedback(chatId, rating, { sessionId });
      ratedChatIds.current.add(chatId);
      setMsgs((p) =>
        p.map((m, i) =>
          i === promptIdx ? { ...m, status: "submitted", rating } : m,
        ),
      );
    } catch {
      setMsgs((p) =>
        p.map((m, i) => (i === promptIdx ? { ...m, status: "error" } : m)),
      );
    }
  };

  const scrollToSource = (msgIdx, refNumber) => {
    const el = document.getElementById(`src-${msgIdx}-${refNumber}`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("cw-src-flash");
    setTimeout(() => el.classList.remove("cw-src-flash"), 1200);
  };

  const renderAnswerWithCitations = (text, sources, msgIdx) => {
    if (!text) return null;
    if (!sources || sources.length === 0) return text;

    const sourceByRef = new Map(sources.map((s) => [s.ref_number, s]));
    const parts = [];
    const re = /\[(\d+)\]/g;
    let lastIdx = 0;
    let match;
    let key = 0;
    while ((match = re.exec(text)) !== null) {
      if (match.index > lastIdx) {
        parts.push(text.slice(lastIdx, match.index));
      }
      const refNum = parseInt(match[1], 10);
      const src = sourceByRef.get(refNum);
      if (src) {
        const tooltip = `${src.document_title || src.source_file}${
          src.page_number != null ? ` (х.${src.page_number})` : ""
        }\n\n${src.snippet || ""}`;
        parts.push(
          <button
            key={`cite-${msgIdx}-${key++}`}
            type="button"
            className="cw-cite"
            onClick={() => scrollToSource(msgIdx, refNum)}
            title={tooltip}
            aria-label={`Эх сурвалж ${refNum}`}
          >
            [{refNum}]
          </button>,
        );
      } else {
        parts.push(match[0]);
      }
      lastIdx = match.index + match[0].length;
    }
    if (lastIdx < text.length) parts.push(text.slice(lastIdx));
    return parts;
  };

  // Render a single feedback-prompt message (pending / submitting / submitted).
  const renderFeedbackPrompt = (m, i) => {
    if (m.status === "submitted") {
      return (
        <div key={i} className="cw-msg assistant cw-feedback-card">
          <p className="cw-feedback-thanks">
            {FEEDBACK_THANKS_TEXT}
            {m.rating != null && (
              <span className="cw-feedback-thanks-rating"> ({m.rating}/5)</span>
            )}
          </p>
        </div>
      );
    }
    if (m.status === "error") {
      return (
        <div key={i} className="cw-msg assistant cw-feedback-card err">
          <p>Үнэлгээ илгээхэд алдаа гарлаа. Дахин оролдоно уу.</p>
          <div className="cw-rating-row">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                className="cw-rating-btn"
                onClick={() => submitRating(i, m.targetChatId, n)}
                aria-label={`${n} оноо`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
      );
    }
    // pending or submitting
    const disabled = m.status === "submitting";
    return (
      <div key={i} className="cw-msg assistant cw-feedback-card">
        <p>{FEEDBACK_PROMPT_TEXT}</p>
        <div className="cw-rating-row">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              className={`cw-rating-btn${
                disabled && m.rating === n ? " is-active" : ""
              }`}
              onClick={() => submitRating(i, m.targetChatId, n)}
              disabled={disabled}
              aria-label={`${n} оноо`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>
    );
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
            {msgs.map((m, i) => {
              // Render the inactivity-triggered feedback prompt separately.
              if (m.role === "system" && m.kind === "feedback-prompt") {
                return renderFeedbackPrompt(m, i);
              }
              return (
                <div
                  key={i}
                  className={`cw-msg ${m.role}${m.err ? " err" : ""}`}
                >
                  <p>
                    {m.role === "assistant" && !m.err
                      ? renderAnswerWithCitations(m.content, m.sources, i)
                      : m.content}
                  </p>
                  {m.role === "assistant" &&
                    !m.err &&
                    m.sources &&
                    m.sources.length > 0 && (
                      <div className="cw-sources">
                        <div className="cw-sources-title">Эх сурвалж:</div>
                        <ol className="cw-sources-list">
                          {m.sources.map((s) => {
                            const key = `${i}-${s.ref_number}`;
                            const isExpanded = expandedSrc.has(key);
                            return (
                              <li
                                key={s.ref_number}
                                id={`src-${i}-${s.ref_number}`}
                                className={`cw-src-item${isExpanded ? " expanded" : ""}`}
                                onClick={() => toggleSourceExpanded(key)}
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    toggleSourceExpanded(key);
                                  }
                                }}
                                title={isExpanded ? "Хураах" : "Бүтнээр харах"}
                              >
                                <div className="cw-src-head">
                                  <span className="cw-src-num">
                                    [{s.ref_number}]
                                  </span>
                                  <span className="cw-src-title">
                                    {s.document_title || s.source_file}
                                  </span>
                                  {s.page_number != null &&
                                    s.page_number !== 0 && (
                                      <span className="cw-src-page">
                                        х.{s.page_number}
                                      </span>
                                    )}
                                  <span
                                    className="cw-src-toggle"
                                    aria-hidden="true"
                                  >
                                    {isExpanded ? "▾" : "▸"}
                                  </span>
                                </div>
                                {s.snippet && (
                                  <div className="cw-src-snippet">
                                    {s.snippet}
                                  </div>
                                )}
                                {s.law_references &&
                                  s.law_references.length > 0 && (
                                    <div className="cw-src-laws">
                                      {s.law_references.map((lr, j) => (
                                        <span key={j} className="cw-src-law">
                                          {lr}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                              </li>
                            );
                          })}
                        </ol>
                      </div>
                    )}
                </div>
              );
            })}
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
