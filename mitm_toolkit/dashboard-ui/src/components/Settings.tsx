import { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { RadioGroup, RadioGroupItem } from './ui/radio-group'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from './ui/alert-dialog'
import { Settings as SettingsIcon, Trash2, Sun, Moon, Palette } from 'lucide-react'
import { api } from '../lib/api'

export function Settings() {
  const [backendUrl, setBackendUrl] = useState(
    localStorage.getItem('MITM_BACKEND_URL') || 'http://localhost:8000'
  )
  const [isClearing, setIsClearing] = useState(false)
  const [theme, setTheme] = useState<'light' | 'dark'>(
    (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
  )
  const [codeTheme, setCodeTheme] = useState(
    localStorage.getItem('codeTheme') || 'tomorrow'
  )

  const handleSave = () => {
    localStorage.setItem('MITM_BACKEND_URL', backendUrl)
    localStorage.setItem('theme', theme)
    localStorage.setItem('codeTheme', codeTheme)
    
    // Apply theme immediately
    document.documentElement.classList.remove('light', 'dark')
    document.documentElement.classList.add(theme)
    
    // Reload to apply new settings
    window.location.reload()
  }

  const handleReset = () => {
    localStorage.removeItem('MITM_BACKEND_URL')
    setBackendUrl('http://localhost:8000')
    window.location.reload()
  }

  const handleClearData = async () => {
    setIsClearing(true)
    try {
      const response = await fetch(`${backendUrl}/api/clear`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-Confirm-Clear': 'CONFIRM_CLEAR_ALL_DATA',
        },
      })
      const data = await response.json()
      if (data.success) {
        // Reload to show empty state
        window.location.reload()
      } else {
        alert(`Failed to clear data: ${data.error}`)
      }
    } catch (error) {
      alert(`Failed to clear data: ${error}`)
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          <SettingsIcon className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Dashboard Settings</DialogTitle>
          <DialogDescription>
            Configure the connection to your MITM Toolkit backend.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="backend-url" className="text-right">
              Backend URL
            </Label>
            <Input
              id="backend-url"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              className="col-span-3"
              placeholder="http://localhost:8000"
            />
          </div>
          <div className="text-sm text-muted-foreground">
            <p>The URL where your MITM Toolkit backend is running.</p>
            <p className="mt-2">Default: http://localhost:8000</p>
          </div>
          
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium mb-3">Appearance</h4>
            <div className="space-y-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right">Theme</Label>
                <RadioGroup
                  value={theme}
                  onValueChange={(v) => setTheme(v as 'light' | 'dark')}
                  className="col-span-3 flex gap-4"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="light" id="light" />
                    <Label htmlFor="light" className="flex items-center gap-1 cursor-pointer">
                      <Sun className="w-4 h-4" />
                      Light
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="dark" id="dark" />
                    <Label htmlFor="dark" className="flex items-center gap-1 cursor-pointer">
                      <Moon className="w-4 h-4" />
                      Dark
                    </Label>
                  </div>
                </RadioGroup>
              </div>
              
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="code-theme" className="text-right">
                  Code Theme
                </Label>
                <Select value={codeTheme} onValueChange={setCodeTheme}>
                  <SelectTrigger className="col-span-3">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tomorrow">Tomorrow Night</SelectItem>
                    <SelectItem value="dracula">Dracula</SelectItem>
                    <SelectItem value="github">GitHub Light</SelectItem>
                    <SelectItem value="monokai">Monokai</SelectItem>
                    <SelectItem value="nord">Nord</SelectItem>
                    <SelectItem value="one-dark">One Dark</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          
          <div className="border-t pt-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium">Clear Captured Data</h4>
                <p className="text-sm text-muted-foreground">
                  Remove all captured requests and responses from the database
                </p>
              </div>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button 
                    variant="destructive" 
                    size="sm"
                    disabled={isClearing}
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Clear Data
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently delete all captured requests and responses from the database.
                      This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleClearData}>
                      Clear All Data
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleReset}>
            Reset to Default
          </Button>
          <Button onClick={handleSave}>Save Changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}