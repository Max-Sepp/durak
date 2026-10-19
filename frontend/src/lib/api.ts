import type { RoomSettings, SeatTicket } from './types'

async function post<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    const detail = typeof data?.detail === 'string' ? data.detail : res.statusText
    throw new Error(detail)
  }
  return res.json()
}

export function createRoom(name: string, settings: RoomSettings) {
  return post<SeatTicket>('/api/rooms', { name, settings })
}

export function joinRoom(code: string, name: string) {
  return post<SeatTicket>(`/api/rooms/${encodeURIComponent(code)}/join`, { name })
}

const ticketKey = (code: string) => `durak:ticket:${code}`

export function saveTicket(ticket: SeatTicket) {
  try {
    localStorage.setItem(ticketKey(ticket.code), JSON.stringify(ticket))
  } catch {
    // Storage unavailable; the session just won't survive a refresh.
  }
}

export function loadTicket(code: string): SeatTicket | null {
  try {
    const raw = localStorage.getItem(ticketKey(code))
    return raw ? (JSON.parse(raw) as SeatTicket) : null
  } catch {
    return null
  }
}

export function forgetTicket(code: string) {
  try {
    localStorage.removeItem(ticketKey(code))
  } catch {
    // ignore
  }
}
