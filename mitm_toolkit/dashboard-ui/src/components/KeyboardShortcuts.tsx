import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog'
import { Button } from './ui/button'
import { Keyboard } from 'lucide-react'

const shortcuts = [
  { keys: ['⌘', 'K'], description: 'Focus search' },
  { keys: ['⌘', 'E'], description: 'Export current request' },
  { keys: ['⌘', 'R'], description: 'Refresh data' },
  { keys: ['⌘', '⇧', 'C'], description: 'Copy as cURL' },
  { keys: ['/'], description: 'Quick search' },
  { keys: ['J'], description: 'Select next request' },
  { keys: ['K'], description: 'Select previous request' },
  { keys: ['ESC'], description: 'Clear filters' },
  { keys: ['?'], description: 'Show keyboard shortcuts' },
]

export function KeyboardShortcuts() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" title="Keyboard shortcuts (?)">
          <Keyboard className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogDescription>
            Quick actions to navigate and control the dashboard
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          {shortcuts.map((shortcut, index) => (
            <div key={index} className="flex items-center justify-between">
              <div className="flex gap-1">
                {shortcut.keys.map((key, i) => (
                  <kbd
                    key={i}
                    className="px-2 py-1 text-xs font-semibold text-foreground bg-muted border border-border rounded"
                  >
                    {key}
                  </kbd>
                ))}
              </div>
              <span className="text-sm text-muted-foreground">
                {shortcut.description}
              </span>
            </div>
          ))}
        </div>
        <div className="text-xs text-muted-foreground">
          Note: On Windows/Linux, use Ctrl instead of ⌘
        </div>
      </DialogContent>
    </Dialog>
  )
}