import type { SuitCode } from './types'

export const SUIT_SYMBOL: Record<SuitCode, string> = { C: '♣', D: '♦', H: '♥', S: '♠' }
export const SUIT_NAME: Record<SuitCode, string> = {
  C: 'Clubs',
  D: 'Diamonds',
  H: 'Hearts',
  S: 'Spades',
}

export function parseCard(card: string): { rank: string; suit: SuitCode } {
  return { rank: card.slice(0, -1), suit: card.slice(-1) as SuitCode }
}

export function isRed(suit: SuitCode) {
  return suit === 'H' || suit === 'D'
}
