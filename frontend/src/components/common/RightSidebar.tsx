import { useEffect, useRef, useState, KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { useChat } from '../../hooks/useChat'
import WatchlistPanel from './WatchlistPanel'
import styles from './RightSidebar.module.css'

type PanelType = 'watchlist' | 'chat' | null

export default function RightSidebar() {
  const [activePanel, setActivePanel] = useState<PanelType>(null)
  const [input, setInput] = useState('')
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const sidebarRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const { messages, isLoading, sendMessage, clear } = useChat()

  // 외부 클릭 시 패널 닫기
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(e.target as Node)) {
        setActivePanel(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // 새 메시지 시 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 패널 열릴 때 input 포커스
  useEffect(() => {
    if (activePanel === 'chat') {
      setTimeout(() => inputRef.current?.focus(), 150)
    }
  }, [activePanel])

  const toggle = (panel: PanelType) => {
    if (!user) {
      navigate('/login')
      return
    }
    setActivePanel((prev) => (prev === panel ? null : panel))
  }

  const handleSend = () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    sendMessage(text)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className={styles.sidebar} ref={sidebarRef}>
      {activePanel === 'watchlist' && (
        <div className={styles.panel}>
          <WatchlistPanel />
        </div>
      )}

      {activePanel === 'chat' && (
        <div className={styles.panel}>
          <div className={styles.chatPanel}>
            {/* 헤더 */}
            <div className={styles.chatHeader}>
              <div className={styles.chatHeaderLeft}>
                <div className={styles.chatHeaderIcon}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M8 12h.01M12 12h.01M16 12h.01" strokeWidth="2.5" strokeLinecap="round" />
                  </svg>
                </div>
                <span>AI 투자 도우미</span>
              </div>
              {messages.length > 0 && (
                <button className={styles.clearBtn} onClick={clear} title="대화 초기화">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6l-1 14H6L5 6" />
                    <path d="M10 11v6M14 11v6" />
                  </svg>
                </button>
              )}
            </div>

            {/* 메시지 영역 */}
            <div className={styles.chatMessages}>
              {messages.length === 0 && (
                <div className={styles.chatWelcome}>
                  <div className={styles.welcomeIcon}>
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M8 12h.01M12 12h.01M16 12h.01" strokeWidth="2.5" strokeLinecap="round" />
                    </svg>
                  </div>
                  <p className={styles.welcomeTitle}>무엇이든 물어보세요</p>
                  <div className={styles.suggestions}>
                    {[
                      '오늘 코스피 상황 어때?',
                      '삼성전자 지금 사도 될까?',
                      '거래량 상위 종목 알려줘',
                      'KODEX ETF 추천해줘',
                    ].map((s) => (
                      <button key={s} className={styles.suggestionBtn} onClick={() => sendMessage(s)}>
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                  {msg.role === 'assistant' && (
                    <div className={styles.msgAvatar}>AI</div>
                  )}
                  <div className={`${styles.msgBubble} ${msg.isError ? styles.errorBubble : ''}`}>
                    {/* Tool 호출 표시 */}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className={styles.toolCalls}>
                        {msg.toolCalls.map((label, j) => (
                          <div key={j} className={styles.toolCall}>
                            <span className={styles.toolDot} />
                            {label}
                          </div>
                        ))}
                      </div>
                    )}
                    {/* 메시지 내용 */}
                    {msg.content && (
                      <div className={styles.msgText}>
                        <MarkdownText text={msg.content} />
                      </div>
                    )}
                    {/* 로딩 중이고 내용이 없을 때 */}
                    {isLoading && i === messages.length - 1 && !msg.content && (
                      <div className={styles.typing}>
                        <span /><span /><span />
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* 입력 영역 */}
            <div className={styles.chatInput}>
              <textarea
                ref={inputRef}
                className={styles.inputArea}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="메시지를 입력하세요... (Enter 전송)"
                rows={1}
                disabled={isLoading}
              />
              <button
                className={styles.sendBtn}
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={styles.iconBar}>
        <button
          className={`${styles.iconBtn} ${activePanel === 'chat' ? styles.active : ''}`}
          onClick={() => toggle('chat')}
          title="AI 투자 도우미"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <circle cx="12" cy="12" r="10" />
            <path d="M8 12h.01M12 12h.01M16 12h.01" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          <span>AI</span>
        </button>

        <div className={styles.divider} />

        <button
          className={`${styles.iconBtn} ${activePanel === 'watchlist' ? styles.active : ''}`}
          onClick={() => toggle('watchlist')}
          title="관심 종목"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill={activePanel === 'watchlist' ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
          <span>관심</span>
        </button>
      </div>
    </div>
  )
}

// 간단한 마크다운 렌더러 (볼드, 줄바꿈)
function MarkdownText({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <>
      {lines.map((line, i) => {
        // **bold** 처리
        const parts = line.split(/\*\*(.*?)\*\*/g)
        return (
          <span key={i}>
            {parts.map((part, j) =>
              j % 2 === 1 ? <strong key={j}>{part}</strong> : part,
            )}
            {i < lines.length - 1 && <br />}
          </span>
        )
      })}
    </>
  )
}
