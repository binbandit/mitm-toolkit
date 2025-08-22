import { useState, useEffect } from 'react'
import { CapturedRequest, CapturedResponse } from '../types'
import { api } from '../lib/api'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { ScrollArea } from './ui/scroll-area'
import { Copy, RefreshCw, Terminal, Download, Clock, Database, Shield } from 'lucide-react'
import { format } from 'date-fns'
import { SecurityAnalyzer } from './SecurityAnalyzer'
import { SyntaxHighlight } from './SyntaxHighlight'
import { toast } from 'sonner'

interface RequestDetailsProps {
  requestId: string
}

export function RequestDetails({ requestId }: RequestDetailsProps) {
  const [loading, setLoading] = useState(true)
  const [request, setRequest] = useState<CapturedRequest | null>(null)
  const [response, setResponse] = useState<CapturedResponse | null>(null)
  const [imageError, setImageError] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.getRequestDetail(requestId)
      .then((data: any) => {
        setRequest(data.request)
        setResponse(data.response)
        setLoading(false)
      })
      .catch((err: any) => {
        console.error('Failed to fetch request details:', err)
        setLoading(false)
      })
  }, [requestId])

  const copyToClipboard = (text: string, message?: string) => {
    navigator.clipboard.writeText(text)
    toast.success(message || 'Copied to clipboard')
  }

  const copyAsCurl = () => {
    if (!request) return
    
    let curlCommand = `curl -X ${request.method} '${request.url}'`
    
    // Add headers
    if (request.headers) {
      Object.entries(request.headers).forEach(([key, value]) => {
        if (key.toLowerCase() !== 'host' && key.toLowerCase() !== 'content-length') {
          curlCommand += ` \\\n  -H '${key}: ${value}'`
        }
      })
    }
    
    // Add body if present
    if (request.body && ['POST', 'PUT', 'PATCH'].includes(request.method)) {
      const bodyStr = typeof request.body === 'string' ? request.body : JSON.stringify(request.body)
      curlCommand += ` \\\n  --data '${bodyStr.replace(/'/g, "'\\''")}'`
    }
    
    navigator.clipboard.writeText(curlCommand)
    toast.success('cURL command copied to clipboard')
  }

  const replayRequest = async () => {
    if (!request) return
    
    try {
      // Create a fetch request that mimics the original
      const options: RequestInit = {
        method: request.method,
        headers: request.headers || {},
      }
      
      // Add body for methods that support it
      if (request.body_decoded && ['POST', 'PUT', 'PATCH'].includes(request.method)) {
        options.body = request.body_decoded
      }
      
      // Note: This will be blocked by CORS in most cases
      // In production, this should go through a backend proxy
      toast.info('Replaying request...', {
        description: 'Note: Request may be blocked by CORS policy'
      })
      
      const response = await fetch(request.url, options)
      
      if (response.ok) {
        toast.success('Request replayed successfully', {
          description: `Status: ${response.status}`
        })
      } else {
        toast.error('Request replay failed', {
          description: `Status: ${response.status}`
        })
      }
    } catch (error) {
      toast.error('Request replay failed', {
        description: error instanceof Error ? error.message : 'Unknown error'
      })
    }
  }
  
  const exportRequest = () => {
    if (!request) return
    
    const exportData = {
      request,
      response,
      timestamp: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `request-${request.id}.json`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Request exported successfully')
  }

  const renderResponseBody = (resp: CapturedResponse) => {
    if (!resp.body_decoded) return null
    
    const contentType = resp.headers?.['content-type']?.toLowerCase() || ''
    
    // Handle images
    if (contentType.includes('image/')) {
      const imageType = contentType.split('/')[1]?.split(';')[0]
      
      // For base64 encoded images in the response body
      if (resp.body_decoded.startsWith('data:image')) {
        return (
          <div className="border rounded p-2 bg-muted/30">
            <img 
              src={resp.body_decoded} 
              alt="Response" 
              className="max-w-full h-auto rounded"
              onError={() => setImageError(true)}
            />
          </div>
        )
      }
      
      // Try to create a data URL from the body
      try {
        const dataUrl = `data:${contentType};base64,${btoa(resp.body_decoded)}`
        return (
          <div className="border rounded p-2 bg-muted/30">
            <img 
              src={dataUrl} 
              alt="Response" 
              className="max-w-full h-auto rounded"
              onError={() => setImageError(true)}
            />
          </div>
        )
      } catch (e) {
        // Fall back to showing raw data
      }
    }
    
    // Handle JSON
    if (contentType.includes('application/json') || contentType.includes('text/json')) {
      try {
        const jsonData = JSON.parse(resp.body_decoded)
        return <SyntaxHighlight code={JSON.stringify(jsonData, null, 2)} language="json" />
      } catch (e) {
        // Not valid JSON, show as text
      }
    }
    
    // Handle HTML
    if (contentType.includes('text/html')) {
      return (
        <div className="space-y-2">
          <div className="border rounded p-2 bg-muted/30 max-h-96 overflow-auto">
            <div dangerouslySetInnerHTML={{ __html: resp.body_decoded }} />
          </div>
          <details className="cursor-pointer">
            <summary className="text-xs text-muted-foreground">View Source</summary>
            <div className="mt-2">
              <SyntaxHighlight code={resp.body_decoded} language="markup" />
            </div>
          </details>
        </div>
      )
    }
    
    // Handle XML
    if (contentType.includes('text/xml') || contentType.includes('application/xml')) {
      return <SyntaxHighlight code={resp.body_decoded} language="markup" />
    }
    
    // Handle CSS
    if (contentType.includes('text/css')) {
      return <SyntaxHighlight code={resp.body_decoded} language="css" />
    }
    
    // Handle JavaScript
    if (contentType.includes('application/javascript') || contentType.includes('text/javascript')) {
      return <SyntaxHighlight code={resp.body_decoded} language="javascript" />
    }
    
    // Default: auto-detect language
    return <SyntaxHighlight code={resp.body_decoded} />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!request) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Request not found
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{request.method}</Badge>
            <span className="font-mono text-sm">{request.path}</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={copyAsCurl}
              title="Copy as cURL command"
              className="cursor-pointer"
            >
              <Terminal className="w-4 h-4 mr-1" />
              cURL
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => copyToClipboard(request.id, 'Request ID copied')}
              title="Copy request ID"
              className="cursor-pointer"
            >
              <Copy className="w-4 h-4 mr-1" />
              ID
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={exportRequest}
              title="Export request/response as JSON"
              className="cursor-pointer"
            >
              <Download className="w-4 h-4 mr-1" />
              Export
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={replayRequest}
              title="Replay request"
              className="cursor-pointer"
            >
              <RefreshCw className="w-4 h-4 mr-1" />
              Replay
            </Button>
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          {format(new Date(request.timestamp), 'PPpp')}
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1 w-full">
        <Tabs defaultValue="request" className="p-4 max-w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="request">Request</TabsTrigger>
            <TabsTrigger value="response">Response</TabsTrigger>
            <TabsTrigger value="headers">Headers</TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-1">
              <Shield className="w-3 h-3" />
              Security
            </TabsTrigger>
          </TabsList>

          <TabsContent value="request" className="space-y-4 overflow-x-hidden">
            <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle>Request Details</CardTitle>
                <CardDescription className="truncate">
                  {request.url}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Request ID</h4>
                  <code className="text-xs bg-muted p-2 rounded block overflow-x-auto break-all">
                    {request.id}
                  </code>
                </div>

                {request.query_params && Object.keys(request.query_params).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Query Parameters</h4>
                    <SyntaxHighlight 
                      code={JSON.stringify(request.query_params, null, 2)} 
                      language="json"
                      maxHeight="12rem" 
                    />
                  </div>
                )}

                {request.body_decoded && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Request Body</h4>
                    <div className="mb-2">
                      <Badge variant="secondary" className="text-xs">
                        <Database className="w-3 h-3 mr-1" />
                        {new Blob([request.body_decoded]).size} bytes
                      </Badge>
                    </div>
                    <SyntaxHighlight code={request.body_decoded} />
                  </div>
                )}

                {request.is_rpc && request.rpc_type && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">RPC Information</h4>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Type:</span>
                        <Badge variant="secondary">{request.rpc_type}</Badge>
                      </div>
                      {request.rpc_method && (
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground">Method:</span>
                          <code className="text-sm">{request.rpc_method}</code>
                        </div>
                      )}
                      {request.rpc_batch && (
                        <Badge variant="outline">Batch Request</Badge>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="response" className="space-y-4 overflow-x-hidden">
            <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle>Response Details</CardTitle>
                {response && (
                  <CardDescription>
                    Status: {response.status_code} • Time: {response.response_time?.toFixed(0)}ms
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                {response ? (
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium mb-2">Status Code</h4>
                      <Badge 
                        variant={response.status_code >= 200 && response.status_code < 300 ? "default" : "destructive"}
                      >
                        {response.status_code}
                      </Badge>
                    </div>

                    {response.body_decoded && (
                      <div>
                        <h4 className="text-sm font-medium mb-2">Response Body</h4>
                        <div className="mb-2 flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            <Database className="w-3 h-3 mr-1" />
                            {new Blob([response.body_decoded]).size} bytes
                          </Badge>
                          {response.headers && response.headers['content-type'] && (
                            <Badge variant="outline" className="text-xs">
                              {response.headers['content-type'].split(';')[0]}
                            </Badge>
                          )}
                        </div>
                        {renderResponseBody(response)}
                      </div>
                    )}

                    <div>
                      <h4 className="text-sm font-medium mb-2">Response Time</h4>
                      <span className="text-sm">{response.response_time?.toFixed(2)}ms</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-muted-foreground">No response captured</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="headers" className="space-y-4 overflow-x-hidden">
            <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle>Request Headers</CardTitle>
              </CardHeader>
              <CardContent>
                {request.headers && (
                  <div className="space-y-2">
                    {Object.entries(request.headers).map(([key, value]) => (
                      <div key={key} className="flex">
                        <span className="font-mono text-xs text-muted-foreground w-1/3">
                          {key}:
                        </span>
                        <span className="font-mono text-xs flex-1 break-all">
                          {value}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {response && response.headers && (
              <Card>
                <CardHeader>
                  <CardTitle>Response Headers</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(response.headers).map(([key, value]) => (
                      <div key={key} className="flex">
                        <span className="font-mono text-xs text-muted-foreground w-1/3">
                          {key}:
                        </span>
                        <span className="font-mono text-xs flex-1 break-all">
                          {value}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="security" className="space-y-4 overflow-x-hidden">
            <div className="overflow-x-auto">
              <SecurityAnalyzer request={request} response={response} />
            </div>
          </TabsContent>
        </Tabs>
      </ScrollArea>
    </div>
  )
}