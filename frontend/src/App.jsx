import React, { useState } from "react";
import LandingPage from "./pages/LandingPage";
import ChatWidget from "./components/ChatWidget";

export default function App() {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="brand">
            <div className="brand-mark" aria-hidden="true">
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
              <h1 className="app-title">Тэгшбот</h1>
              <p className="app-subtitle">
                Хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хүртээмжийн талаар
                мэдээлэл өгөх ухаалаг чатбот
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="app-main">
        <LandingPage onOpenChat={() => setChatOpen(true)} />
      </main>

      <ChatWidget open={chatOpen} setOpen={setChatOpen} />
    </div>
  );
}
