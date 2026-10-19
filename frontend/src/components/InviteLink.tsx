import { CheckIcon, CopyIcon } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

function inviteUrl(code: string) {
  return `${location.origin}${location.pathname}?room=${code}`
}

/** Room code with its invite link and a copy button right beside it. */
export function InviteLink({ code, compact, className }: { code: string; compact?: boolean; className?: string }) {
  const [copied, setCopied] = useState(false)
  const url = inviteUrl(code)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      toast.success('Invite link copied')
      setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error('Could not copy, share the code instead')
    }
  }

  return (
    <div className={cn('flex min-w-0 items-center gap-2', className)}>
      <span
        className={cn(
          'rounded-md bg-ctp-surface0 px-2 py-1 font-mono font-semibold tracking-[0.2em] text-ctp-mauve',
          compact ? 'text-sm' : 'text-2xl',
        )}
      >
        {code}
      </span>
      {!compact && (
        <span className="min-w-0 truncate rounded-md border px-2 py-1 font-mono text-xs text-muted-foreground">
          {url}
        </span>
      )}
      <Button
        size={compact ? 'icon-sm' : 'icon'}
        variant="outline"
        onClick={copy}
        aria-label="Copy invite link"
        title="Copy invite link"
      >
        {copied ? <CheckIcon className="text-ctp-green" /> : <CopyIcon />}
      </Button>
    </div>
  )
}
