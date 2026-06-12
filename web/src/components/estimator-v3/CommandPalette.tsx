'use client'

import { useCallback, useEffect, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Command } from 'cmdk'
import {
  Plus,
  GitCompare,
  FileDown,
  History,
  Volume2,
  Square,
  MessageSquare,
  Search,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { type ChatSessionV3 } from '@/lib/api-v3'

export interface CommandPaletteProps {
  loading?: boolean
  voiceReadBack?: boolean
  compareMode?: boolean
  sessions?: ChatSessionV3[]
  onNewEstimate?: () => void
  onCompareVariants?: () => void
  onExportPDF?: () => void
  onViewSessions?: () => void
  onToggleVoiceReadBack?: () => void
  onStopGenerating?: () => void
  onSelectSession?: (session: ChatSessionV3) => void
}

function CommandItem({
  icon: Icon,
  label,
  onSelect,
  shortcut,
}: {
  icon: LucideIcon
  label: string
  onSelect: () => void
  shortcut?: string
}) {
  return (
    <Command.Item
      onSelect={onSelect}
      className={cn(
        'flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors text-[color:var(--muted-ink)]',
        'hover:bg-[color:var(--panel-strong)]',
        'data-[selected=true]:bg-[color:var(--panel-strong)] data-[selected=true]:text-[color:var(--ink)]'
      )}
    >
      <Icon size={15} className="shrink-0" />
      <span className="flex-1 truncate">{label}</span>
      {shortcut && (
        <kbd className="shrink-0 rounded bg-[color:var(--panel-strong)] px-1.5 py-0.5 text-[10px] text-[color:var(--muted-ink)]">
          {shortcut}
        </kbd>
      )}
    </Command.Item>
  )
}

export function CommandPalette({
  loading = false,
  voiceReadBack = false,
  compareMode = false,
  sessions = [],
  onNewEstimate,
  onCompareVariants,
  onExportPDF,
  onViewSessions,
  onToggleVoiceReadBack,
  onStopGenerating,
  onSelectSession,
}: CommandPaletteProps) {
  const [open, setOpen] = useState(false)

  // Listen for the estimator-specific command palette event.
  // This avoids opening both the global and estimator palettes at the same time.
  useEffect(() => {
    const handler = () => setOpen(true)
    window.addEventListener('show-estimator-command-palette', handler)
    return () => window.removeEventListener('show-estimator-command-palette', handler)
  }, [])

  const close = useCallback(() => setOpen(false), [])

  const run = useCallback(
    (fn?: () => void) => {
      fn?.()
      close()
    },
    [close]
  )

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[18%] z-50 w-full max-w-lg -translate-x-1/2 overflow-hidden rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] shadow-2xl focus:outline-none">
          <Command
            label="Command palette"
            className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1.5 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-bold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-widest [&_[cmdk-group-heading]]:text-[color:var(--muted-ink)]"
          >
            <div className="flex items-center gap-3 border-b border-[color:var(--line)] px-4 py-3">
              <Search size={16} className="shrink-0 text-[color:var(--muted-ink)]" />
              <Command.Input
                placeholder="Type a command..."
                className="w-full bg-transparent text-base text-[color:var(--ink)] placeholder:text-[color:var(--muted-ink)] outline-none"
              />
              <kbd className="shrink-0 rounded bg-[color:var(--panel-strong)] px-1.5 py-0.5 text-[10px] text-[color:var(--muted-ink)]">
                ESC
              </kbd>
            </div>
            <Command.List className="max-h-[360px] overflow-y-auto overscroll-contain p-2">
              <Command.Empty className="px-3 py-6 text-center text-sm text-[color:var(--muted-ink)]">
                No results found
              </Command.Empty>

              <Command.Group heading="Actions">
                <CommandItem
                  icon={Plus}
                  label="New estimate"
                  onSelect={() => run(onNewEstimate)}
                />
                <CommandItem
                  icon={GitCompare}
                  label={compareMode ? 'Disable compare variants' : 'Compare variants'}
                  onSelect={() => run(onCompareVariants)}
                />
                <CommandItem
                  icon={FileDown}
                  label="Export to PDF"
                  onSelect={() => run(onExportPDF)}
                />
                <CommandItem
                  icon={History}
                  label="View sessions"
                  onSelect={() => run(onViewSessions)}
                />
                <CommandItem
                  icon={Volume2}
                  label={voiceReadBack ? 'Disable voice read-back' : 'Toggle voice read-back'}
                  onSelect={() => run(onToggleVoiceReadBack)}
                />
                {loading && (
                  <CommandItem
                    icon={Square}
                    label="Stop generating"
                    onSelect={() => run(onStopGenerating)}
                  />
                )}
              </Command.Group>

              {sessions.length > 0 && (
                <Command.Group heading="Recent sessions">
                  {sessions.map((session) => (
                    <CommandItem
                      key={session.id}
                      icon={MessageSquare}
                      label={session.title || 'Untitled conversation'}
                      onSelect={() => run(() => onSelectSession?.(session))}
                    />
                  ))}
                </Command.Group>
              )}
            </Command.List>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
