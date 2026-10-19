import { useCallback, useState } from 'react'
import { toast } from 'sonner'
import { AppShell } from '@/components/AppShell'
import { Button } from '@/components/ui/button'
import { Toaster } from '@/components/ui/sonner'
import { forgetTicket, loadTicket } from '@/lib/api'
import { useGameSocket } from '@/lib/socket'
import type { SeatTicket } from '@/lib/types'
import { Home } from '@/pages/Home'
import { Lobby } from '@/pages/Lobby'
import { Table } from '@/pages/Table'

function roomFromUrl() {
  return new URLSearchParams(location.search).get('room')?.toUpperCase() ?? ''
}

function setUrlRoom(code: string | null) {
  const url = new URL(location.href)
  if (code) url.searchParams.set('room', code)
  else url.searchParams.delete('room')
  history.replaceState(null, '', url)
}

export default function App() {
  const [urlCode] = useState(roomFromUrl)
  const [ticket, setTicket] = useState<SeatTicket | null>(() => (urlCode ? loadTicket(urlCode) : null))

  const enter = (t: SeatTicket) => {
    setUrlRoom(t.code)
    setTicket(t)
  }

  const leave = () => {
    if (ticket) forgetTicket(ticket.code)
    setUrlRoom(null)
    setTicket(null)
  }

  return (
    <>
      {ticket ? (
        <RoomScreen key={ticket.token} ticket={ticket} onLeave={leave} />
      ) : (
        <Home initialCode={urlCode} onEnter={enter} />
      )}
      <Toaster position="top-center" />
    </>
  )
}

function RoomScreen({ ticket, onLeave }: { ticket: SeatTicket; onLeave: () => void }) {
  const onError = useCallback((message: string) => toast.error(message), [])
  const { room, game, status, send, reconnect } = useGameSocket(ticket.code, ticket.token, onError)

  if (status === 'replaced') {
    return (
      <AppShell className="max-w-md items-center justify-center gap-4 text-center">
        <p>This game was opened in another tab or on another device.</p>
        <Button onClick={reconnect}>Play here instead</Button>
      </AppShell>
    )
  }
  if (status === 'rejected') {
    return (
      <AppShell className="max-w-md items-center justify-center gap-4">
        <p>This room no longer exists or your seat is invalid.</p>
        <Button onClick={onLeave}>Back to home</Button>
      </AppShell>
    )
  }
  if (!room) {
    return (
      <AppShell className="items-center justify-center text-muted-foreground">Connecting…</AppShell>
    )
  }

  return (
    <>
      {status !== 'open' && (
        <div className="fixed inset-x-0 top-0 z-50 bg-ctp-yellow py-1 text-center text-sm text-ctp-base">
          Reconnecting…
        </div>
      )}
      {game ? (
        <Table
          room={room}
          game={game}
          onAction={(action) => send({ type: 'action', action })}
          onRematch={() => send({ type: 'rematch' })}
          onLeave={onLeave}
        />
      ) : (
        <Lobby room={room} onStart={() => send({ type: 'start' })} onLeave={onLeave} />
      )}
    </>
  )
}
