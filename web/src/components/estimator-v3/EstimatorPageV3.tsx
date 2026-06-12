'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useSearchParams } from 'next/navigation'
import { chatApiV3, type IntakeResultV3, type RevisionSuggestionV3 } from '@/lib/api-v3'
import { useSpeechSynthesis } from '@/lib/speech'
import { haptic } from '@/lib/haptics'

import { ChatContainer } from './ChatContainer'
import { CommandPalette } from './CommandPalette'
import { ShortcutsHelp } from './ShortcutsHelp'
import { useChatOrchestrator, useInputComposer, useEstimateActions } from './hooks'

interface EstimatorPageV3Props {
  projectId?: number
}

export function EstimatorPageV3({ projectId }: EstimatorPageV3Props) {
  useSearchParams() // triggers suspense boundary if needed
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [keyboardOffset, setKeyboardOffset] = useState(0)

  const tts = useSpeechSynthesis({ rate: 1.1 })
  const bottomSentinelRef = useRef<HTMLDivElement>(null)

  // Track on-screen keyboard height
  useEffect(() => {
    const viewport = window.visualViewport
    if (!viewport) return
    const handler = () => {
      const offset = window.innerHeight - viewport.height - viewport.offsetTop
      setKeyboardOffset(Math.max(0, offset))
    }
    viewport.addEventListener('resize', handler)
    viewport.addEventListener('scroll', handler)
    return () => {
      viewport.removeEventListener('resize', handler)
      viewport.removeEventListener('scroll', handler)
    }
  }, [])

  // Initialize orchestrator
  const orchestrator = useChatOrchestrator({ county: 'Dallas', projectId })

  // Initialize input composer with send callback
  const composer = useInputComposer({
    onSend: (message, { compareMode }) => {
      orchestrator.sendMessage({ message, compareMode })
    },
  })

  // Initialize estimate actions with orchestrator setters
  const estimateActions = useEstimateActions({
    onMessagesChange: updater => orchestrator.setMessages(updater(orchestrator.messages)),
    onSelectedMessageChange: orchestrator.setSelectedMessage,
    onSheetOpenChange: orchestrator.setSheetOpen,
    onCompareVariantsChange: orchestrator.setCompareVariants,
  })

  // Restore session on mount + auto-focus
  useEffect(() => {
    orchestrator.restoreSession()
    composer.focusInput()
  }, [orchestrator, composer])

  // Voice read-back: speak estimate summary when selected message changes
  useEffect(() => {
    if (!composer.voiceReadBack || !orchestrator.selectedMessage?.estimate) return
    const est = orchestrator.selectedMessage.estimate
    const text = `Estimate: $${est.grand_total.toFixed(0)}. Labor: $${est.labor_total.toFixed(0)}. Materials: $${est.materials_total.toFixed(0)}.`
    tts.speak(text)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orchestrator.selectedMessage?.estimate_id, composer.voiceReadBack, tts])

  // Auto-scroll to bottom on new messages / loading
  useEffect(() => {
    bottomSentinelRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [orchestrator.messages, orchestrator.loading])

  const handleCopy = useCallback((id: string, content: string) => {
    navigator.clipboard.writeText(content)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }, [])

  const handleSuggestion = useCallback((text: string) => {
    haptic('tap')
    composer.setInput(text)
    const message = composer.composeMessage()
    if (message.trim()) {
      orchestrator.sendMessage({ message, compareMode: composer.compareMode })
      composer.clear()
    }
  }, [composer, orchestrator])

  const handleClarificationAnswer = useCallback((answer: string) => {
    orchestrator.handleClarificationAnswer(answer, (msg: string) => {
      composer.setInput(msg)
      const composed = composer.composeMessage()
      if (composed.trim()) {
        orchestrator.sendMessage({ message: composed, compareMode: composer.compareMode })
        composer.clear()
      }
    })
  }, [orchestrator, composer])

  const handleLoadAndSelectSession = useCallback(async (sessionId: number) => {
    try {
      const res = await chatApiV3.getSession(sessionId)
      const loaded = res.data.messages.map(m => ({
        id: `sess-${m.id}`,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        timestamp: new Date(m.created_at || Date.now()),
        estimate_id: m.estimate_id,
      }))
      orchestrator.setMessages(loaded)
      orchestrator.sessionIdRef.current = String(sessionId)
      try { sessionStorage.setItem('v3_chat_session_id', String(sessionId)) } catch { /* noop */ }
      orchestrator.setSessionsOpen(false)
    } catch {
      // ignore
    }
  }, [orchestrator])

  const handleDeleteSession = useCallback(async (sessionId: number) => {
    try {
      await chatApiV3.deleteSession(sessionId)
      orchestrator.setSessions(prev => prev.filter(x => x.id !== sessionId))
    } catch { /* ignore */ }
  }, [orchestrator])

  const handleNewConversation = useCallback(() => {
    orchestrator.handleNewConversation()
    composer.clear()
    setTimeout(() => composer.focusInput(), 0)
  }, [orchestrator, composer])

  // Message actions
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleEditMessage = useCallback((id: string, _content: string) => {
    orchestrator.editMessage(id, (text: string) => {
      composer.setInput(text)
      composer.focusInput()
    })
  }, [orchestrator, composer])

  const handleRegenerateMessage = useCallback((id: string) => {
    orchestrator.regenerateMessage(id, (message: string) => {
      orchestrator.sendMessage({ message, compareMode: composer.compareMode })
    })
  }, [orchestrator, composer])

  const handleDeleteMessage = useCallback((id: string) => {
    orchestrator.deleteMessage(id)
  }, [orchestrator])

  const handleRefine = useCallback((prompt: string) => {
    composer.setInput(prompt)
    const message = composer.composeMessage()
    if (message.trim()) {
      orchestrator.sendMessage({ message, compareMode: composer.compareMode })
      composer.clear()
    }
  }, [composer, orchestrator])

  const handleConfirmIntake = useCallback((intake: IntakeResultV3) => {
    orchestrator.confirmIntake(intake)
  }, [orchestrator])

  const buildRevisionPrompt = useCallback((suggestion: RevisionSuggestionV3): string => {
    const delta = suggestion.delta || {}
    const target = String(delta.target || delta.item || delta.fixture_type || '').replace(/_/g, ' ')
    const to = String(delta.to || delta.material_upgrade || '').replace(/_/g, ' ')
    const fromValue = String(delta.from || '').replace(/_/g, ' ')
    switch (suggestion.action) {
      case 'upgrade':
        return target && to ? `Upgrade ${target} to ${to}` : suggestion.label
      case 'add':
        return target ? `Add ${target}` : suggestion.label
      case 'remove':
        return target ? `Remove ${target}` : suggestion.label
      case 'swap':
        return fromValue && to ? `Swap ${fromValue} to ${to}` : (target && to ? `Swap ${target} to ${to}` : suggestion.label)
      case 'quantity': {
        const qty = Number(delta.quantity_delta ?? delta.quantity ?? 0)
        const item = target || suggestion.label.replace(/^Add /, '').replace(/^Remove /, '')
        if (qty === 0) return suggestion.label
        return `${qty > 0 ? 'Add' : 'Remove'} ${Math.abs(qty)} ${item}`.trim()
      }
      default:
        return suggestion.label
    }
  }, [])

  const handleRevisionSuggestion = useCallback((suggestion: RevisionSuggestionV3) => {
    haptic('tap')
    const prompt = buildRevisionPrompt(suggestion)
    composer.setInput(prompt)
    const message = composer.composeMessage()
    if (message.trim()) {
      orchestrator.sendMessage({ message, compareMode: composer.compareMode })
      composer.clear()
    }
  }, [composer, orchestrator, buildRevisionPrompt])

  // Command palette action handlers
  const handlePaletteNewEstimate = useCallback(() => {
    handleNewConversation()
  }, [handleNewConversation])

  const handlePaletteCompare = useCallback(() => {
    composer.toggleCompareMode()
  }, [composer])

  const handlePaletteViewSessions = useCallback(() => {
    orchestrator.loadSessions()
    orchestrator.setSessionsOpen(true)
  }, [orchestrator])

  const handlePaletteSelectSession = useCallback((session: { id: number }) => {
    handleLoadAndSelectSession(session.id)
  }, [handleLoadAndSelectSession])

  return (
    <>
      <ChatContainer
        keyboardOffset={keyboardOffset}
        county="Dallas"
        messages={orchestrator.messages}
        loading={orchestrator.loading}
        onStopGenerating={orchestrator.stopGenerating}
        selectedMessage={orchestrator.selectedMessage}
        sheetOpen={orchestrator.sheetOpen}
        onSetSheetOpen={orchestrator.setSheetOpen}
        onViewBreakdown={orchestrator.handleViewBreakdown}
        copiedId={copiedId}
        onCopyMessage={handleCopy}
        onFeedback={estimateActions.handleFeedback}
        feedbackState={estimateActions.feedbackState}
        estimateRecommendations={estimateActions.estimateRecommendations}
        input={composer.input}
        setInput={composer.setInput}
        onSubmit={composer.handleSubmit}
        handleKeyDown={(e) => composer.handleKeyDown(e, { onEditLast: () => {
          // Find last user message and edit it
          const lastUser = orchestrator.messages.slice().reverse().find(m => m.role === 'user')
          if (lastUser) {
            orchestrator.editMessage(lastUser.id, (text: string) => {
              composer.setInput(text)
              composer.focusInput()
            })
          }
        } })}
        inputRef={composer.inputRef}
        disabled={orchestrator.loading}
        imagePreview={composer.imagePreview}
        imageAnalyzing={composer.imageAnalyzing}
        blueprintSummary={composer.blueprintSummary}
        attachedImage={composer.attachedImage}
        onRemoveImage={composer.handleRemoveImage}
        fileInputRef={composer.fileInputRef}
        onFileSelect={composer.handleFileSelect}
        speechSupported={composer.speech.supported}
        speechListening={composer.speech.listening}
        onToggleSpeech={() => {
          haptic('tap')
          if (composer.speech.listening) {
            composer.speech.stop()
          } else {
            composer.speech.reset()
            composer.speech.start()
          }
        }}
        voiceReadBack={composer.voiceReadBack}
        onToggleVoiceReadBack={composer.toggleVoiceReadBack}
        ttsSupported={tts.supported}
        suggestedContext={orchestrator.suggestedContext}
        onDismissSuggestions={() => orchestrator.setSuggestedContext([])}
        onSuggestionClick={handleSuggestion}
        compareMode={composer.compareMode}
        onToggleCompareMode={composer.toggleCompareMode}
        compareVariants={orchestrator.compareVariants}
        onDismissCompare={() => orchestrator.setCompareVariants(null)}
        onAdoptVariant={estimateActions.adoptVariant}
        sessions={orchestrator.sessions}
        sessionsOpen={orchestrator.sessionsOpen}
        onSetSessionsOpen={orchestrator.setSessionsOpen}
        onLoadSessions={orchestrator.loadSessions}
        onSelectSession={handleLoadAndSelectSession}
        onDeleteSession={handleDeleteSession}
        onNewConversation={handleNewConversation}
        clarificationQuestions={orchestrator.clarificationQuestions}
        onClarificationAnswer={handleClarificationAnswer}
        onDismissClarification={() => orchestrator.setClarificationQuestions(null)}
        // Sprint 2: message actions
        onEditMessage={handleEditMessage}
        onRegenerateMessage={handleRegenerateMessage}
        onDeleteMessage={handleDeleteMessage}
        streamingMessageId={orchestrator.streamingMessageId}
        onRefine={handleRefine}
        pendingIntake={orchestrator.pendingIntake}
        onConfirmIntake={handleConfirmIntake}
        onRevisionSuggestionClick={handleRevisionSuggestion}
        sessionId={orchestrator.sessionId}
      />

      <CommandPalette
        loading={orchestrator.loading}
        voiceReadBack={composer.voiceReadBack}
        compareMode={composer.compareMode}
        sessions={orchestrator.sessions}
        onNewEstimate={handlePaletteNewEstimate}
        onCompareVariants={handlePaletteCompare}
        onViewSessions={handlePaletteViewSessions}
        onToggleVoiceReadBack={composer.toggleVoiceReadBack}
        onStopGenerating={orchestrator.stopGenerating}
        onSelectSession={handlePaletteSelectSession}
      />

      <ShortcutsHelp />

      <div ref={bottomSentinelRef} className="sr-only" aria-hidden="true" />
    </>
  )
}
