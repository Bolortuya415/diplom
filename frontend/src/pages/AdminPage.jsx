import React, { useState, useEffect } from 'react'
import { uploadDocument, getDocuments, getHealth, getStats } from '../services/api'

export default function AdminPage() {
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [documents, setDocuments] = useState([])
  const [health, setHealth] = useState(null)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [docs, h, s] = await Promise.all([
        getDocuments(),
        getHealth(),
        getStats(),
      ])
      setDocuments(docs)
      setHealth(h)
      setStats(s)
    } catch (err) {
      console.error('Failed to load admin data:', err)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setUploadResult(null)

    try {
      const result = await uploadDocument(file, title || null)
      setUploadResult({ success: true, ...result })
      setFile(null)
      setTitle('')
      loadData()
    } catch (err) {
      setUploadResult({ success: false, error: err.message })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="admin-page">
      <section className="admin-section">
        <h2>Баримт бичиг оруулах</h2>
        <div className="upload-form">
          <input
            type="file"
            accept=".pdf,.txt"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <input
            type="text"
            placeholder="Баримт бичгийн нэр (заавал биш)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <button onClick={handleUpload} disabled={!file || uploading}>
            {uploading ? 'Оруулж байна...' : 'Оруулах'}
          </button>
        </div>

        {uploadResult && (
          <div className={`upload-result ${uploadResult.success ? 'success' : 'error'}`}>
            {uploadResult.success ? (
              <p>
                Амжилттай! {uploadResult.filename}: {uploadResult.pages} хуудас,{' '}
                {uploadResult.chunks} хэсэг
              </p>
            ) : (
              <p>Алдаа: {uploadResult.error}</p>
            )}
          </div>
        )}
      </section>

      <section className="admin-section">
        <h2>Системийн мэдээлэл</h2>
        {health && (
          <div className="health-info">
            <div className="stat-card">
              <span className="stat-label">Статус</span>
              <span className="stat-value">{health.status}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Индекс</span>
              <span className="stat-value">{health.index_loaded ? 'Бэлэн' : 'Бэлэн биш'}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Нийт хэсэг</span>
              <span className="stat-value">{health.total_chunks}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Ангилагч</span>
              <span className="stat-value">{health.classifier_loaded ? 'Ачаалсан' : 'Ачаалаагүй'}</span>
            </div>
          </div>
        )}
      </section>

      {stats && (
        <section className="admin-section">
          <h2>Хэрэглээний статистик</h2>
          <div className="health-info">
            <div className="stat-card">
              <span className="stat-label">Нийт чат</span>
              <span className="stat-value">{stats.total_chats}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Сэтгэл ханамж</span>
              <span className="stat-value">{stats.positive_feedback}/{stats.total_feedback}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Аюулгүй бус асуулт</span>
              <span className="stat-value">{stats.unsafe_queries}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Дундаж хариу (мс)</span>
              <span className="stat-value">{stats.avg_response_time_ms}</span>
            </div>
          </div>
        </section>
      )}

      <section className="admin-section">
        <h2>Баримт бичгүүд ({documents.length})</h2>
        {documents.length === 0 ? (
          <p className="empty-state">Баримт бичиг оруулаагүй байна.</p>
        ) : (
          <table className="docs-table">
            <thead>
              <tr>
                <th>Нэр</th>
                <th>Файл</th>
                <th>Хуудас</th>
                <th>Хэсэг</th>
                <th>Огноо</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.title}</td>
                  <td>{doc.filename}</td>
                  <td>{doc.page_count}</td>
                  <td>{doc.chunk_count}</td>
                  <td>{new Date(doc.upload_date).toLocaleDateString('mn-MN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
