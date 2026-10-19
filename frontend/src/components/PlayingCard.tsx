import { cn } from '@/lib/utils'
import { isRed, parseCard, SUIT_SYMBOL } from '@/lib/cards'

const SIZES = {
  sm: 'w-10 h-14 text-xs',
  md: 'w-14 h-20 text-sm sm:w-16 sm:h-24 sm:text-base',
} as const

interface PlayingCardProps {
  card: string
  size?: keyof typeof SIZES
  selected?: boolean
  playable?: boolean
  disabled?: boolean
  onClick?: () => void
  className?: string
}

export function PlayingCard({
  card,
  size = 'md',
  selected,
  playable,
  disabled,
  onClick,
  className,
}: PlayingCardProps) {
  const { rank, suit } = parseCard(card)
  const symbol = SUIT_SYMBOL[suit]
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      disabled={onClick ? disabled : undefined}
      aria-label={`${rank} of ${suit}`}
      className={cn(
        'relative flex shrink-0 select-none flex-col justify-between rounded-md border border-ctp-surface1 bg-ctp-base p-1 font-semibold shadow-sm transition',
        isRed(suit) ? 'text-ctp-red' : 'text-ctp-text',
        SIZES[size],
        onClick && !disabled && 'hover:-translate-y-1',
        playable && 'ring-2 ring-ctp-green',
        selected && '-translate-y-2 ring-2 ring-ctp-peach',
        disabled && 'opacity-60',
        className,
      )}
    >
      <span className="leading-none">
        {rank}
        <span className="block">{symbol}</span>
      </span>
      <span className="self-center text-xl leading-none sm:text-2xl">{symbol}</span>
      <span className="rotate-180 self-end leading-none">
        {rank}
        <span className="block">{symbol}</span>
      </span>
    </Tag>
  )
}

export function CardBack({ size = 'md', className }: { size?: keyof typeof SIZES; className?: string }) {
  return (
    <div
      className={cn(
        'shrink-0 rounded-md border-2 border-ctp-base bg-[repeating-linear-gradient(45deg,var(--ctp-mauve)_0_6px,var(--ctp-lavender)_6px_12px)] shadow-sm',
        SIZES[size],
        className,
      )}
    />
  )
}
