import { useState } from 'react'
import { Button } from './ui/button'
import { Download, Upload, FileJson } from 'lucide-react'
import { CapturedRequest, CapturedResponse } from '../types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog'
import { Input } from './ui/input'
import { api } from '../lib/api'

interface HarExportProps {
  requests: CapturedRequest[]
  onImport?: (requests: CapturedRequest[]) => void
}

export function HarExport({ requests, onImport }: HarExportProps) {
  const [importing, setImporting] = useState(false)

  const exportToHar = async () => {
    // Fetch full request details for all requests
    const fullRequests = await Promise.all(
      requests.map(async (req) => {
        try {
          const detail = await api.getRequestDetail(req.id)
          return { request: req, response: detail.response }
        } catch {
          return { request: req, response: null }
        }
      })
    )

    const har = {
      log: {
        version: '1.2',
        creator: {
          name: 'MITM Toolkit',
          version: '1.0.0'
        },
        entries: fullRequests.map(({ request, response }) => ({
          startedDateTime: request.timestamp,
          time: response?.response_time || 0,
          request: {
            method: request.method,
            url: request.url,
            httpVersion: request.http_version || 'HTTP/1.1',
            cookies: [],
            headers: Object.entries(request.headers || {}).map(([name, value]) => ({
              name,
              value
            })),
            queryString: Object.entries(request.query_params || {}).map(([name, value]) => ({
              name,
              value
            })),
            postData: request.body_decoded ? {
              mimeType: request.headers?.['content-type'] || 'application/octet-stream',
              text: request.body_decoded
            } : undefined,
            headersSize: -1,
            bodySize: request.body_decoded ? new Blob([request.body_decoded]).size : 0
          },
          response: response ? {
            status: response.status_code,
            statusText: '',
            httpVersion: request.http_version || 'HTTP/1.1',
            cookies: [],
            headers: Object.entries(response.headers || {}).map(([name, value]) => ({
              name,
              value
            })),
            content: {
              size: response.body_decoded ? new Blob([response.body_decoded]).size : 0,
              mimeType: response.headers?.['content-type'] || 'application/octet-stream',
              text: response.body_decoded || ''
            },
            redirectURL: '',
            headersSize: -1,
            bodySize: response.body_decoded ? new Blob([response.body_decoded]).size : 0
          } : {
            status: 0,
            statusText: '',
            httpVersion: 'HTTP/1.1',
            cookies: [],
            headers: [],
            content: { size: 0, mimeType: 'application/octet-stream' },
            redirectURL: '',
            headersSize: -1,
            bodySize: -1
          },
          cache: {},
          timings: {
            blocked: -1,
            dns: -1,
            connect: -1,
            send: -1,
            wait: response?.response_time || -1,
            receive: -1,
            ssl: -1
          },
          serverIPAddress: request.host,
          connection: request.id
        }))
      }
    }

    const blob = new Blob([JSON.stringify(har, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mitm-capture-${new Date().toISOString()}.har`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleFileImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setImporting(true)
    try {
      const text = await file.text()
      const har = JSON.parse(text)
      
      if (!har.log?.entries) {
        throw new Error('Invalid HAR file format')
      }

      // Convert HAR entries back to CapturedRequest format
      const importedRequests: CapturedRequest[] = har.log.entries.map((entry: any, index: number) => ({
        id: `imported-${Date.now()}-${index}`,
        timestamp: entry.startedDateTime,
        method: entry.request.method,
        url: entry.request.url,
        path: new URL(entry.request.url).pathname,
        host: new URL(entry.request.url).hostname,
        http_version: entry.request.httpVersion,
        headers: entry.request.headers?.reduce((acc: any, h: any) => {
          acc[h.name] = h.value
          return acc
        }, {}),
        query_params: entry.request.queryString?.reduce((acc: any, q: any) => {
          acc[q.name] = q.value
          return acc
        }, {}),
        body_decoded: entry.request.postData?.text,
        status_code: entry.response.status,
        response_time: entry.time,
        is_rpc: false,
        rpc_type: null,
        rpc_method: null,
        rpc_batch: false
      }))

      onImport?.(importedRequests)
    } catch (error) {
      console.error('Failed to import HAR file:', error)
      alert('Failed to import HAR file. Please check the file format.')
    } finally {
      setImporting(false)
      if (e.target) e.target.value = ''
    }
  }

  return (
    <div className="flex gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={exportToHar}
        disabled={requests.length === 0}
      >
        <Download className="w-4 h-4 mr-1" />
        Export HAR
      </Button>
      
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <Upload className="w-4 h-4 mr-1" />
            Import HAR
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import HAR File</DialogTitle>
            <DialogDescription>
              Import a HAR (HTTP Archive) file to analyze captured traffic
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="flex items-center gap-4">
              <FileJson className="w-8 h-8 text-muted-foreground" />
              <Input
                type="file"
                accept=".har,application/json"
                onChange={handleFileImport}
                disabled={importing}
              />
            </div>
            {importing && (
              <p className="text-sm text-muted-foreground">Importing HAR file...</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}