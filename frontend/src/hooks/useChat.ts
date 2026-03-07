import { useState, useRef, useCallback } from 'react'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  toolCalls?: string[]
  isError?: boolean
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (text: string) => {
      if (isLoading) return

      const userMsg: ChatMessage = { role: 'user', content: text }
      const history = [...messages, userMsg]
      setMessages(history)
      setIsLoading(true)

      // 빈 assistant 슬롯 추가
      const assistantMsg: ChatMessage = { role: 'assistant', content: '', toolCalls: [] }
      setMessages([...history, assistantMsg])

      const controller = new AbortController()
      abortRef.current = controller

      try {
        const token = localStorage.getItem('access_token') || ''
        const response = await fetch('/api/v1/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            messages: history.map((m) => ({ role: m.role, content: m.content })),
          }),
          signal: controller.signal,
        })

        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        if (!response.body) throw new Error('No response body')

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            let data: { type: string; text?: string; label?: string; message?: string }
            try {
              data = JSON.parse(line.slice(6))
            } catch {
              continue
            }

            if (data.type === 'tool_start' && data.label) {
              setMessages((prev) => {
                const last = { ...prev[prev.length - 1] }
                last.toolCalls = [...(last.toolCalls ?? []), data.label!]
                return [...prev.slice(0, -1), last]
              })
            } else if (data.type === 'text_delta' && data.text) {
              setMessages((prev) => {
                const last = { ...prev[prev.length - 1] }
                last.content += data.text
                return [...prev.slice(0, -1), last]
              })
            } else if (data.type === 'error') {
              setMessages((prev) => {
                const last = { ...prev[prev.length - 1] }
                last.content = data.message ?? '오류가 발생했습니다.'
                last.isError = true
                return [...prev.slice(0, -1), last]
              })
            } else if (data.type === 'done') {
              break
            }
          }
        }
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        setMessages((prev) => {
          const last = { ...prev[prev.length - 1] }
          last.content = '연결 오류가 발생했습니다. 다시 시도해주세요.'
          last.isError = true
          return [...prev.slice(0, -1), last]
        })
      } finally {
        setIsLoading(false)
        abortRef.current = null
      }
    },
    [messages, isLoading],
  )

  const clear = useCallback(() => setMessages([]), [])

  const abort = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { messages, isLoading, sendMessage, clear, abort }
}
