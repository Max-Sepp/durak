import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { AppShell } from '@/components/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { createRoom, joinRoom, saveTicket } from '@/lib/api'
import { RULES, type RuleKey, type SeatTicket } from '@/lib/types'

const NAME_KEY = 'durak:name'
const DEFAULT_NAME = 'Ada'
const ROOM_CODE_LENGTH = 6 // matches CODE_LENGTH in backend rooms.py

function loadName() {
  try {
    return localStorage.getItem(NAME_KEY) || DEFAULT_NAME
  } catch {
    return DEFAULT_NAME
  }
}

function storeName(name: string) {
  try {
    localStorage.setItem(NAME_KEY, name)
  } catch {
    // ignore
  }
}

export function Home({ initialCode, onEnter }: { initialCode: string; onEnter: (t: SeatTicket) => void }) {
  const [name, setName] = useState(loadName)
  const [code, setCode] = useState(initialCode)
  const [deckSize, setDeckSize] = useState('52')
  const [rules, setRules] = useState<Record<RuleKey, boolean>>({
    transfer_enabled: true,
    trump_swap_enabled: true,
    all_players_throw_in: true,
    throw_in_after_take: true,
  })
  const [busy, setBusy] = useState(false)

  const enter = async (request: () => Promise<SeatTicket>) => {
    if (!name.trim()) {
      toast.error('Enter your name first')
      return
    }
    setBusy(true)
    try {
      const ticket = await request()
      storeName(name.trim())
      saveTicket(ticket)
      onEnter(ticket)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  const onCreate = (e: FormEvent) => {
    e.preventDefault()
    enter(() =>
      createRoom(name.trim(), {
        deck_size: Number(deckSize) as 36 | 52,
        ...rules,
      }),
    )
  }

  const onJoin = (e: FormEvent) => {
    e.preventDefault()
    enter(() => joinRoom(code.trim().toUpperCase(), name.trim()))
  }

  return (
    <AppShell className="max-w-md gap-6">
      <section className="py-4 text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Play <span className="text-ctp-mauve">Durak</span>
        </h1>
        <p className="text-muted-foreground">Don't be the fool holding the last cards.</p>
      </section>

      <div className="grid gap-2">
        <Label htmlFor="name">Your name</Label>
        <Input
          id="name"
          value={name}
          maxLength={24}
          onChange={(e) => setName(e.target.value)}
          placeholder={DEFAULT_NAME}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Join a room</CardTitle>
          <CardDescription>Enter the code a friend shared with you.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onJoin} className="flex gap-2">
            <Input
              aria-label="Room code"
              value={code}
              maxLength={ROOM_CODE_LENGTH}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="ABCDEF"
              className="font-mono tracking-widest uppercase"
            />
            <Button type="submit" disabled={busy || code.trim().length !== ROOM_CODE_LENGTH}>
              Join
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Create a room</CardTitle>
          <CardDescription>You'll be the host and can start once others join.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onCreate} className="grid gap-4">
            <div className="flex items-center justify-between gap-4">
              <Label>Deck</Label>
              <Select value={deckSize} onValueChange={setDeckSize}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="36">36 cards</SelectItem>
                  <SelectItem value="52">52 cards</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {RULES.map(({ key, label, description }) => (
              <div key={key} className="flex items-center justify-between gap-4">
                <Label htmlFor={key} className="flex flex-col items-start gap-0.5">
                  {label}
                  <span className="text-xs font-normal text-muted-foreground">{description}</span>
                </Label>
                <Switch
                  id={key}
                  checked={rules[key]}
                  onCheckedChange={(on) => setRules((r) => ({ ...r, [key]: on }))}
                />
              </div>
            ))}
            <Button type="submit" disabled={busy}>
              Create room
            </Button>
          </form>
        </CardContent>
      </Card>
    </AppShell>
  )
}
