import { useState, useEffect } from 'react'
import { CapturedRequest, CapturedResponse } from '../types'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { ScrollArea } from './ui/scroll-area'
import { Separator } from './ui/separator'
import { Copy, ExternalLink, RefreshCw } from 'lucide-react'
import { format } from 'date-fns'

interface RequestDetailsProps {
  requestId: string
}

export function RequestDetails({ requestId }: RequestDetailsProps) {
  const [loading, setLoading] = useState(true)
  const [request, setRequest] = useState<CapturedRequest | null>(null)
  const [response, setResponse] = useState<CapturedResponse | null>(null)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/request/${requestId}`)
      .then(res => res.json())
      .then(data => {
        setRequest(data.request)
        setResponse(data.response)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch request details:', err)
        setLoading(false)
      })
  }, [requestId])

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const replayRequest = async () => {
    // TODO: Implement replay functionality
    console.log('Replay request:', requestId)
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
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{request.method}</Badge>
            <span className="font-mono text-sm">{request.path}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => copyToClipboard(request.id)}
            >
              <Copy className="w-4 h-4 mr-1" />
              Copy ID
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={replayRequest}
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
      <ScrollArea className="flex-1">
        <Tabs defaultValue="request" className="p-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="request">Request</TabsTrigger>
            <TabsTrigger value="response">Response</TabsTrigger>
            <TabsTrigger value="headers">Headers</TabsTrigger>
          </TabsList>

          <TabsContent value="request" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Request Details</CardTitle>
                <CardDescription>
                  {request.url}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Request ID</h4>
                  <code className="text-xs bg-muted p-2 rounded block">
                    {request.id}
                  </code>
                </div>

                {request.query_params && Object.keys(request.query_params).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Query Parameters</h4>
                    <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                      {JSON.stringify(request.query_params, null, 2)}
                    </pre>
                  </div>
                )}

                {request.body_decoded && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Request Body</h4>
                    <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                      {request.body_decoded}
                    </pre>
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

          <TabsContent value="response" className="space-y-4">
            <Card>
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
                        <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                          {response.body_decoded}
                        </pre>
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

          <TabsContent value="headers" className="space-y-4">
            <Card>
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
        </Tabs>
      </ScrollArea>
    </div>
  )
}