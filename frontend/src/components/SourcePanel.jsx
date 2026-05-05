import React from 'react'

export default function SourcePanel({ sources, onClose }) {
  return (
    <div className="source-panel">
      <div className="source-panel-header">
        <h3>Эх сурвалжууд</h3>
        <button className="close-btn" onClick={onClose}>X</button>
      </div>
      <div className="source-list">
        {sources.map((src, i) => (
          <div key={i} className="source-item">
            <div className="source-ref">[{src.ref_number}]</div>
            <div className="source-details">
              {/* Human-readable document title */}
              <div className="source-file">
                {src.document_title || src.source_file}
              </div>

              {/* Raw filename (secondary, smaller) */}
              {src.document_title && (
                <div className="source-filename">{src.source_file}</div>
              )}

              {src.page_number && (
                <div className="source-page">Хуудас: {src.page_number}</div>
              )}

              {/* Law article references */}
              {src.law_references && src.law_references.length > 0 && (
                <div className="source-law-refs">
                  {src.law_references.map((ref, j) => (
                    <span key={j} className="law-ref-badge">{ref}</span>
                  ))}
                </div>
              )}

              <div className="source-score">
                Хамааралтай байдал:{" "}
                {isFinite(src.relevance_score)
                  ? (src.relevance_score * 100).toFixed(1) + "%"
                  : "—"}
              </div>
              <div className="source-snippet">{src.snippet}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
