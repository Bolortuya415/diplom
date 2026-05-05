import React from 'react'

export default function MessageBubble({ message, onFeedback, onShowSources }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message ${message.role} ${message.error ? 'error' : ''}`}>
      <div className="message-content">
        <p>{message.content}</p>
      </div>

      {!isUser && !message.error && (
        <div className="message-actions">
          {message.sources && message.sources.length > 0 && (
            <button className="action-btn source-btn" onClick={onShowSources}>
              Эх сурвалж ({message.sources.length})
            </button>
          )}

          {message.chatId && (
            <div className="feedback-buttons">
              <button
                className={`action-btn ${message.feedbackGiven === 1 ? 'active' : ''}`}
                onClick={() => onFeedback(1)}
                disabled={message.feedbackGiven !== null}
                title="Сайн хариулт"
              >
                +
              </button>
              <button
                className={`action-btn ${message.feedbackGiven === -1 ? 'active' : ''}`}
                onClick={() => onFeedback(-1)}
                disabled={message.feedbackGiven !== null}
                title="Муу хариулт"
              >
                -
              </button>
            </div>
          )}

          {message.responseTime && (
            <span className="response-time">{message.responseTime}мс</span>
          )}
        </div>
      )}
    </div>
  )
}
