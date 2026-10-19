import { AppShell } from '@/components/AppShell'
import { InviteLink } from '@/components/InviteLink'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RULES, type RoomInfo } from '@/lib/types'

export function Lobby({ room, onStart, onLeave }: { room: RoomInfo; onStart: () => void; onLeave: () => void }) {
  const isHost = room.you === room.host_seat
  const { deck_size } = room.settings
  const full = room.seats.length >= room.max_players

  return (
    <AppShell
      className="max-w-md gap-6"
      actions={
        <Button size="sm" variant="ghost" onClick={onLeave}>
          Leave
        </Button>
      }
    >
      <Card>
        <CardHeader>
          <CardDescription>Share this room code or link with your friends</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <InviteLink code={room.code} />
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{deck_size} cards</Badge>
            {RULES.filter(({ key }) => room.settings[key]).map(({ key, label }) => (
              <Badge key={key} variant="secondary">
                {label}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Players ({room.seats.length})</CardTitle>
          {full && (
            <CardDescription className="text-ctp-peach">
              Room is full ({room.max_players} players max)
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="grid gap-2">
          {room.seats.map((seat, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg bg-ctp-surface0/60 px-3 py-2">
              <span className="font-medium">
                {seat.name}
                {i === room.you && <span className="text-muted-foreground"> (you)</span>}
              </span>
              <span className="flex gap-1">
                {i === room.host_seat && <Badge>Host</Badge>}
                {!seat.connected && <Badge variant="outline">offline</Badge>}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      {isHost ? (
        <Button size="lg" onClick={onStart} disabled={room.seats.length < 2}>
          {room.seats.length < 2 ? 'Waiting for players…' : 'Start game'}
        </Button>
      ) : (
        <p className="text-center text-muted-foreground">Waiting for the host to start…</p>
      )}
    </AppShell>
  )
}
