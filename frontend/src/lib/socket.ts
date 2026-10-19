import { useCallback, useEffect, useRef, useState } from 'react'
import type { ClientMessage, GameSnapshot, RoomInfo, ServerMessage } from './types'

export type SocketStatus = 'connecting' | 'open' | 'closed' | 'rejected' | 'replaced'

// Server close codes (see backend ws.py) that must not trigger a reconnect.
const REJECTED_CODES = new Set([4401, 4403, 4404])
const REPLACED_CODE = 4409

/** Connects to a room, keeps the latest snapshot, and reconnects on drops. */
export function useGameSocket(code: string, token: string, onError: (message: string) => void) {
  const [room, setRoom] = useState<RoomInfo | null>(null)
  const [game, setGame] = useState<GameSnapshot | null>(null)
  const [status, setStatus] = useState<SocketStatus>('connecting')
  const [attemptKey, setAttemptKey] = useState(0)
  const socketRef = useRef<WebSocket | null>(null)
  const onErrorRef = useRef(onError)
  useEffect(() => {
    onErrorRef.current = onError
  })

  useEffect(() => {
    let cancelled = false
    let retryTimer: number | undefined
    let attempt = 0

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/ws/${encodeURIComponent(code)}`)
      socketRef.current = ws
      setStatus('connecting')

      ws.onopen = () => {
        // The token goes in the first message, never the URL, so it stays out of logs.
        ws.send(JSON.stringify({ type: 'auth', token }))
        attempt = 0
        setStatus('open')
      }
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data) as ServerMessage
        if (msg.type === 'room') {
          setRoom(msg.room)
          setGame(msg.game)
        } else {
          onErrorRef.current(msg.message)
        }
      }
      ws.onclose = (event) => {
        if (cancelled) return
        if (REJECTED_CODES.has(event.code)) {
          setStatus('rejected')
          return
        }
        if (event.code === REPLACED_CODE) {
          setStatus('replaced')
          return
        }
        setStatus('closed')
        const delay = Math.min(1000 * 2 ** attempt, 10_000)
        attempt += 1
        retryTimer = window.setTimeout(connect, delay)
      }
    }

    connect()
    return () => {
      cancelled = true
      window.clearTimeout(retryTimer)
      const ws = socketRef.current
      if (!ws) return
      ws.onmessage = null
      if (ws.readyState === WebSocket.CONNECTING) {
        // Closing mid-handshake (e.g. StrictMode's double effect in dev) makes the
        // Vite proxy write to a dead socket and log EPIPE; close once it opens.
        ws.onopen = () => ws.close()
      } else {
        ws.close()
      }
    }
  }, [code, token, attemptKey])

  const send = useCallback((msg: ClientMessage) => {
    const ws = socketRef.current
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg))
  }, [])

  /** Reconnect after the seat was taken over by another tab or device. */
  const reconnect = useCallback(() => setAttemptKey((k) => k + 1), [])

  return { room, game, status, send, reconnect }
}
