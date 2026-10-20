// Mirrors the server protocol in backend/src/durak_server (rooms.py snapshot)
// and durak_engine (views.py / actions.py).

export type SuitCode = 'C' | 'D' | 'H' | 'S'

export interface RoomSettings {
  deck_size: 36 | 52
  transfer_enabled: boolean
  trump_swap_enabled: boolean
  all_players_throw_in: boolean
  throw_in_after_take: boolean
  first_out_wins: boolean
}

export type RuleKey = 'transfer_enabled' | 'trump_swap_enabled' | 'all_players_throw_in' | 'throw_in_after_take' | 'first_out_wins'

export const RULES: { key: RuleKey; label: string; description: string }[] = [
  { key: 'transfer_enabled', label: 'Transfer', description: 'Defender may pass the attack on with a card of the same rank' },
  { key: 'trump_swap_enabled', label: 'Trump swap', description: 'Lowest trump can be swapped for the face-up trump' },
  { key: 'all_players_throw_in', label: 'Everyone piles on', description: 'All players may throw in, not just the attacker' },
  { key: 'throw_in_after_take', label: 'Pile on after take', description: 'Cards can still be added once the defender takes' },
  { key: 'first_out_wins', label: 'First out wins', description: 'The first player to get rid of all their cards wins' },
]

export interface SeatTicket {
  code: string
  token: string
  seat: number
}

export interface RoomInfo {
  code: string
  settings: RoomSettings
  seats: { name: string; connected: boolean }[]
  host_seat: number
  max_players: number
  you: number
  started: boolean
}

export interface TablePair {
  attack: string
  defense: string | null
}

export interface PlayerView {
  you: number
  hand: string[]
  hand_counts: number[]
  talon_count: number
  trump_card: string | null
  trump_suit: SuitCode
  table: TablePair[]
  attacker: number
  defender: number
  phase: 'attacking' | 'defender_taking' | 'finished'
  passed: number[]
  out_order: number[]
  durak: number | null
  winner: number | null
  discard_count: number
  bout_limit: number
  transfer_enabled: boolean
}

export type Action =
  | { kind: 'attack'; card: string }
  | { kind: 'defend'; attack_index: number; card: string }
  | { kind: 'transfer'; card: string }
  | { kind: 'take' }
  | { kind: 'pass' }
  | { kind: 'swap_trump' }

export interface GameEvent {
  kind: string
  player: number | null
  [key: string]: unknown
}

export interface GameSnapshot {
  view: PlayerView
  legal_actions: Action[]
  events: GameEvent[]
}

export type ServerMessage =
  | { type: 'room'; room: RoomInfo; game: GameSnapshot | null }
  | { type: 'error'; message: string }

export type ClientMessage =
  | { type: 'start' }
  | { type: 'rematch' }
  | { type: 'action'; action: Action }
