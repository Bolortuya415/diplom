import React, { useState } from 'react'
import LandingPage from './pages/LandingPage'
import ChatPage from './pages/ChatPage'
import AdminPage from './pages/AdminPage'

export default function App() {
  const [page, setPage] = useState('landing')
  const [category, setCategory] = useState(null)

  const handleSelectCategory = (catId) => {
    setCategory(catId)
    setPage('chat')
  }

  const handleBackToLanding = () => {
    setCategory(null)
    setPage('landing')
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="brand">
            <div
              className="brand-mark"
              aria-hidden="true"
              style={{ cursor: 'pointer' }}
              onClick={handleBackToLanding}
            >
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
                <path
                  d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div className="brand-text">
              <h1
                className="app-title"
                style={{ cursor: 'pointer' }}
                onClick={handleBackToLanding}
              >
                Тэгшбот
              </h1>
              <p className="app-subtitle">
                Хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хөгжлийн бэрхшээлтэй
                иргэдийн эрхийн талаар мэдээлэл өгөх ухаалаг чатбот
              </p>
            </div>
          </div>

          <nav className="app-nav" aria-label="Үндсэн цэс">
            <button
              className={`nav-btn ${page === 'landing' || page === 'chat' ? 'active' : ''}`}
              onClick={handleBackToLanding}
            >
              Нүүр
            </button>
            <button
              className={`nav-btn ${page === 'admin' ? 'active' : ''}`}
              onClick={() => setPage('admin')}
            >
              Админ
            </button>
          </nav>
        </div>
      </header>

      <main className="app-main">
        {page === 'landing' && (
          <LandingPage onSelectCategory={handleSelectCategory} />
        )}
        {page === 'chat' && (
          <ChatPage category={category} onBack={handleBackToLanding} />
        )}
        {page === 'admin' && <AdminPage />}
      </main>
    </div>
  )
}
