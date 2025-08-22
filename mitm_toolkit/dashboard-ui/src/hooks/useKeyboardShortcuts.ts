import { useEffect } from 'react'

interface ShortcutHandlers {
  onSearch?: () => void
  onClearFilters?: () => void
  onExport?: () => void
  onRefresh?: () => void
  onToggleTheme?: () => void
  onSelectNext?: () => void
  onSelectPrevious?: () => void
  onCopyAsCurl?: () => void
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if user is typing in an input field
      const isTyping = ['INPUT', 'TEXTAREA'].includes(
        (e.target as HTMLElement).tagName
      )
      
      // Cmd/Ctrl + K - Focus search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        handlers.onSearch?.()
      }
      
      // Cmd/Ctrl + E - Export
      if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
        e.preventDefault()
        handlers.onExport?.()
      }
      
      // Cmd/Ctrl + R - Refresh
      if ((e.metaKey || e.ctrlKey) && e.key === 'r') {
        e.preventDefault()
        handlers.onRefresh?.()
      }
      
      // Cmd/Ctrl + Shift + C - Copy as cURL
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'C') {
        e.preventDefault()
        handlers.onCopyAsCurl?.()
      }
      
      // Don't handle these if typing
      if (!isTyping) {
        // J - Select next
        if (e.key === 'j') {
          e.preventDefault()
          handlers.onSelectNext?.()
        }
        
        // K - Select previous
        if (e.key === 'k') {
          e.preventDefault()
          handlers.onSelectPrevious?.()
        }
        
        // / - Focus search
        if (e.key === '/') {
          e.preventDefault()
          handlers.onSearch?.()
        }
        
        // Escape - Clear filters
        if (e.key === 'Escape') {
          handlers.onClearFilters?.()
        }
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handlers])
}