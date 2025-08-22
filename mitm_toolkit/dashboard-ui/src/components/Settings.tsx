import { useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog'
import { Settings as SettingsIcon } from 'lucide-react'

export function Settings() {
  const [backendUrl, setBackendUrl] = useState(
    localStorage.getItem('MITM_BACKEND_URL') || 'http://localhost:8000'
  )

  const handleSave = () => {
    localStorage.setItem('MITM_BACKEND_URL', backendUrl)
    // Reload to apply new settings
    window.location.reload()
  }

  const handleReset = () => {
    localStorage.removeItem('MITM_BACKEND_URL')
    setBackendUrl('http://localhost:8000')
    window.location.reload()
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