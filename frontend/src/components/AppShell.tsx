import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/** Shared page frame: the same header and background on every screen. */
export function AppShell({
  actions,
  children,
  className,
}: {
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="sticky top-0 z-40 border-b bg-ctp-mantle/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-3 px-4">
          <span className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <span className="text-ctp-mauve">♠</span>
            Durak
            <span className="text-ctp-red">♥</span>
          </span>
          {actions && <div className="flex min-w-0 items-center gap-2">{actions}</div>}
        </div>
      </header>
      <main className={cn('mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-6', className)}>
        {children}
      </main>
    </div>
  )
}
