import { useMemo, useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { InviteLink } from '@/components/InviteLink'
import { CardBack, PlayingCard } from '@/components/PlayingCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { SUIT_NAME, SUIT_SYMBOL, isRed } from '@/lib/cards'
import type { Action, GameEvent, GameSnapshot, RoomInfo } from '@/lib/types'
import { cn } from '@/lib/utils'

interface TableProps {
  room: RoomInfo
  game: GameSnapshot
  onAction: (action: Action) => void
  onRematch: () => void
  onLeave: () => void
}

export function Table({ room, game, onAction, onRematch, onLeave }: TableProps) {
  const { view, legal_actions: legal } = game
  const names = room.seats.map((s) => s.name)
  const me = view.you
  // A selection only applies to the snapshot it was made on, so it clears
  // itself whenever the server sends a new state.
  const [selection, setSelection] = useState<{ game: GameSnapshot; card: string } | null>(null)
  const selected = selection?.game === game ? selection.card : null
  const setSelected = (card: string | null) => setSelection(card ? { game, card } : null)

  const actionsByCard = useMemo(() => {
    const map = new Map<string, Action[]>()
    for (const action of legal) {
      if ('card' in action) map.set(action.card, [...(map.get(action.card) ?? []), action])
    }
    return map
  }, [legal])

  const canTake = legal.some((a) => a.kind === 'take')
  const canPass = legal.some((a) => a.kind === 'pass')
  const canSwap = legal.some((a) => a.kind === 'swap_trump')
  const transferOption =
    selected !== null ? legal.find((a) => a.kind === 'transfer' && a.card === selected) : undefined
  const defendTargets = new Set(
    legal.flatMap((a) => (a.kind === 'defend' && a.card === selected ? [a.attack_index] : [])),
  )

  const onHandClick = (card: string) => {
    const options = actionsByCard.get(card) ?? []
    const attack = options.find((a) => a.kind === 'attack')
    if (attack) return onAction(attack)
    const defends = options.filter((a) => a.kind === 'defend')
    const canTransfer = options.some((a) => a.kind === 'transfer')
    if (defends.length === 1 && !canTransfer) return onAction(defends[0])
    setSelected(selected === card ? null : card)
  }

  const onTableClick = (index: number) => {
    if (selected && defendTargets.has(index)) {
      onAction({ kind: 'defend', attack_index: index, card: selected })
    }
  }

  const opponents = Array.from({ length: names.length - 1 }, (_, i) => (me + 1 + i) % names.length)
  const finished = view.phase === 'finished'

  const myTurn = legal.some((a) => a.kind !== 'swap_trump')

  return (
    <AppShell
      className="gap-4"
      actions={
        <>
          <InviteLink code={room.code} compact />
          <Button size="sm" variant="ghost" onClick={onLeave}>
            Leave
          </Button>
        </>
      }
    >
      <div
        className={cn(
          'self-center rounded-full px-4 py-1.5 text-center text-sm font-medium',
          myTurn ? 'bg-ctp-mauve text-primary-foreground' : 'bg-ctp-surface0 text-foreground',
        )}
      >
        {statusText(view, myTurn, names)}
      </div>

      <section className="flex flex-wrap justify-center gap-3">
        {opponents.map((p) => (
          <SeatPanel key={p} seat={p} room={room} game={game} />
        ))}
      </section>

      <section className="flex flex-1 flex-col items-center justify-center gap-4 rounded-2xl bg-ctp-mantle p-4 ring-1 ring-foreground/10 sm:flex-row sm:gap-10">
        <div className="flex items-center gap-3">
          <div className="relative flex flex-col items-center gap-1">
            {view.talon_count > 0 ? (
              <div className="relative h-24 w-20 sm:h-28 sm:w-24">
                {view.trump_card && (
                  <PlayingCard card={view.trump_card} className="absolute top-2 left-4 rotate-90" />
                )}
                <CardBack className="absolute top-0 left-0" />
              </div>
            ) : (
              <div className="flex h-20 w-14 items-center justify-center rounded-md border border-dashed border-ctp-overlay text-xs text-muted-foreground sm:h-24 sm:w-16">
                empty
              </div>
            )}
            <span className="text-xs text-muted-foreground">{view.talon_count} in deck</span>
          </div>
          <div className="flex flex-col items-center text-xs">
            <span className={cn('text-3xl', isRed(view.trump_suit) ? 'text-ctp-red' : 'text-foreground')}>
              {SUIT_SYMBOL[view.trump_suit]}
            </span>
            <span>Trump: {SUIT_NAME[view.trump_suit]}</span>
            <span className="text-muted-foreground">{view.discard_count} discarded</span>
          </div>
        </div>

        <div className="flex min-h-28 max-w-2xl flex-1 flex-wrap items-center justify-center gap-3 rounded-xl bg-ctp-crust/60 p-3 sm:min-h-36">
          {view.table.length === 0 && !finished && (
            <span className="text-sm text-muted-foreground">
              {view.attacker === me ? 'Play any card to attack' : `${names[view.attacker]} is attacking…`}
            </span>
          )}
          {view.table.map((pair, i) => {
            const target = defendTargets.has(i)
            return (
              <button
                key={i}
                type="button"
                onClick={() => onTableClick(i)}
                disabled={!target}
                className={cn('relative h-24 w-16 sm:h-30 sm:w-20', target && 'cursor-pointer')}
                aria-label={`Attack ${i + 1}`}
              >
                <PlayingCard card={pair.attack} playable={target} className="absolute top-0 left-0" />
                {pair.defense && (
                  <PlayingCard card={pair.defense} className="absolute top-4 left-3 rotate-12" />
                )}
              </button>
            )
          })}
        </div>
      </section>

      {finished ? (
        <section className="flex flex-col items-center gap-3 py-2">
          {room.settings.first_out_wins ? (
            <p className={cn('text-2xl font-bold', view.winner === me ? 'text-ctp-green' : 'text-ctp-red')}>
              {view.winner === null
                ? "It's a draw!"
                : view.winner === me
                  ? 'You win!'
                  : `${names[view.winner]} wins!`}
            </p>
          ) : (
            <p className={cn('text-2xl font-bold', view.durak === me ? 'text-ctp-red' : 'text-ctp-green')}>
              {view.durak === null
                ? "It's a draw!"
                : view.durak === me
                  ? 'You are the durak!'
                  : `${names[view.durak]} is the durak!`}
            </p>
          )}
          <Button size="lg" onClick={onRematch}>
            Play again
          </Button>
        </section>
      ) : (
        <section className="flex min-h-10 flex-wrap items-center justify-center gap-2">
          {canSwap && view.trump_card && (
            <Button variant="secondary" onClick={() => onAction({ kind: 'swap_trump' })}>
              Swap your low trump for {view.trump_card}
            </Button>
          )}
          {transferOption && (
            <Button variant="secondary" onClick={() => onAction(transferOption)}>
              Transfer with {selected}
            </Button>
          )}
          {canTake && (
            <Button variant="destructive" onClick={() => onAction({ kind: 'take' })}>
              Take cards
            </Button>
          )}
          {canPass && (
            <Button variant="secondary" onClick={() => onAction({ kind: 'pass' })}>
              {view.phase === 'defender_taking' ? 'Done adding' : 'Bito (done)'}
            </Button>
          )}
          {selected && (
            <span className="text-sm text-muted-foreground">
              {defendTargets.size > 0 ? 'Now click the card to beat' : 'Choose an action'}
            </span>
          )}
        </section>
      )}

      <section className="rounded-2xl bg-card px-2 pt-3 pb-4 ring-1 ring-foreground/10">
        <div className="mb-2 flex items-center justify-center gap-2 text-sm">
          <span className="font-medium">{names[me]} (you)</span>
          <RoleBadges seat={me} room={room} game={game} />
        </div>
        <div className="flex justify-center overflow-x-auto px-2 pt-3 pb-1">
          <div className="flex gap-1 sm:gap-2">
            {view.hand.map((card) => {
              const playable = actionsByCard.has(card)
              return (
                <PlayingCard
                  key={card}
                  card={card}
                  playable={playable && selected !== card}
                  selected={selected === card}
                  disabled={!playable}
                  onClick={() => onHandClick(card)}
                />
              )
            })}
          </div>
        </div>
        {game.events.length > 0 && (
          <p className="mt-3 text-center text-xs text-muted-foreground">{describeEvents(game.events, names)}</p>
        )}
      </section>
    </AppShell>
  )
}

function SeatPanel({ seat, room, game }: { seat: number; room: RoomInfo; game: GameSnapshot }) {
  const count = game.view.hand_counts[seat]
  const info = room.seats[seat]
  return (
    <div className="flex min-w-28 flex-col items-center gap-1 rounded-xl bg-card px-3 py-2 ring-1 ring-foreground/10">
      <span className="flex items-center gap-1 text-sm font-medium">
        {info.name}
        {!info.connected && <span className="text-xs text-muted-foreground">(offline)</span>}
      </span>
      <div className="flex h-14 items-center">
        {Array.from({ length: Math.min(count, 6) }, (_, i) => (
          <CardBack key={i} size="sm" className={i > 0 ? '-ml-7' : ''} />
        ))}
        <span className="ml-2 text-sm">{count}</span>
      </div>
      <RoleBadges seat={seat} room={room} game={game} />
    </div>
  )
}

function RoleBadges({ seat, room, game }: { seat: number; room: RoomInfo; game: GameSnapshot }) {
  const { view } = game
  if (view.phase === 'finished' && room.settings.first_out_wins) {
    return view.winner === seat ? <Badge>Winner</Badge> : null
  }
  if (view.phase === 'finished') {
    return view.durak === seat ? <Badge variant="destructive">Durak</Badge> : <Badge>Safe</Badge>
  }
  if (view.out_order.includes(seat)) return <Badge>Out</Badge>
  return (
    <span className="flex gap-1">
      {view.attacker === seat && <Badge variant="secondary">Attacker</Badge>}
      {view.defender === seat && (
        <Badge variant={view.phase === 'defender_taking' ? 'destructive' : 'outline'}>
          {view.phase === 'defender_taking' ? 'Taking' : 'Defender'}
        </Badge>
      )}
      {view.passed.includes(seat) && <Badge variant="outline">Done</Badge>}
    </span>
  )
}

function statusText(view: GameSnapshot['view'], canAct: boolean, names: string[]) {
  if (view.phase === 'finished') return 'Game over'
  const me = view.you
  if (view.out_order.includes(me)) return "You're out — watching"
  if (view.defender === me) {
    if (view.phase === 'defender_taking') return 'Taking — others may add cards'
    return view.table.length ? 'Defend, or take the cards' : `${names[view.attacker]} is attacking you`
  }
  if (canAct) return view.table.length ? 'Add cards or say bito' : 'Your attack'
  return `${names[view.defender]} is defending`
}

function describeEvents(events: GameEvent[], names: string[]) {
  const who = (p: number | null) => (p === null ? 'Nobody' : names[p])
  return events
    .map((e) => {
      switch (e.kind) {
        case 'attack':
          return `${who(e.player)} played ${e.card}`
        case 'defend':
          return `${who(e.player)} beat with ${e.card}`
        case 'transfer':
          return `${who(e.player)} transferred to ${who(e.to as number)}`
        case 'take':
          return `${who(e.player)} takes`
        case 'pass':
          return `${who(e.player)} is done`
        case 'trump_swap':
          return `${who(e.player)} swapped ${e.card} for ${e.took}`
        case 'bout_beaten':
          return 'Bito'
        case 'bout_taken':
          return `${who(e.player)} picked up ${e.count} cards`
        case 'player_out':
          return `${who(e.player)} is out`
        case 'game_over':
          return e.player === null ? 'Draw' : `${who(e.player)} is the durak`
        case 'game_won':
          return e.player === null ? 'Draw' : `${who(e.player)} wins`
        default:
          return null
      }
    })
    .filter(Boolean)
    .join(' · ')
}
