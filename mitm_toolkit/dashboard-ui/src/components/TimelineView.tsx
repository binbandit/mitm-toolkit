import { useMemo } from 'react'
import { CapturedRequest } from '../types'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Clock, Activity } from 'lucide-react'
import { format } from 'date-fns'

interface TimelineViewProps {
  requests: CapturedRequest[]
  onSelectRequest: (id: string) => void
  selectedRequest: string | null
}

export function TimelineView({ requests, onSelectRequest, selectedRequest }: TimelineViewProps) {
  const timeline = useMemo(() => {
    if (requests.length === 0) return { entries: [], duration: 0, startTime: 0 }
    
    // Sort by timestamp
    const sorted = [...requests].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
    
    const startTime = new Date(sorted[0].timestamp).getTime()
    const endTime = new Date(sorted[sorted.length - 1].timestamp).getTime()
    
    // Calculate positions for waterfall
    const entries = sorted.map(req => {
      const reqStart = new Date(req.timestamp).getTime()
      const offset = reqStart - startTime
      const duration = req.response_time || 50 // Default 50ms if no response time
      
      return {
        request: req,
        offset,
        duration,
        startPercent: (offset / (endTime - startTime)) * 100,
        widthPercent: Math.max(0.5, (duration / (endTime - startTime)) * 100)
      }
    })
    
    return {
      entries,
      duration: endTime - startTime,
      startTime
    }
  }, [requests])
  
  const getStatusColor = (status?: number) => {
    if (!status) return 'bg-gray-500'
    if (status >= 200 && status < 300) return 'bg-green-500'
    if (status >= 300 && status < 400) return 'bg-blue-500'
    if (status >= 400 && status < 500) return 'bg-yellow-500'
    if (status >= 500) return 'bg-red-500'
    return 'bg-gray-500'
  }
  
  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET': return 'text-blue-600'
      case 'POST': return 'text-green-600'
      case 'PUT': return 'text-yellow-600'
      case 'DELETE': return 'text-red-600'
      case 'PATCH': return 'text-purple-600'
      default: return 'text-gray-600'
    }
  }
  
  if (requests.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <div className="text-center">
          <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No requests to display in timeline</p>
        </div>
      </div>
    )
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Request Timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Time scale */}
          <div className="flex justify-between text-xs text-muted-foreground mb-2">
            <span>0ms</span>
            <span>{Math.round(timeline.duration / 2)}ms</span>
            <span>{Math.round(timeline.duration)}ms</span>
          </div>
          
          {/* Waterfall chart */}
          <div className="space-y-1 max-h-96 overflow-y-auto">
            {timeline.entries.map(entry => (
              <div
                key={entry.request.id}
                className={`group flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                  selectedRequest === entry.request.id 
                    ? 'bg-accent' 
                    : 'hover:bg-accent/50'
                }`}
                onClick={() => onSelectRequest(entry.request.id)}
              >
                {/* Method and path */}
                <div className="flex-shrink-0 w-48 flex items-center gap-2">
                  <span className={`text-xs font-medium ${getMethodColor(entry.request.method)}`}>
                    {entry.request.method}
                  </span>
                  <span className="text-xs truncate" title={entry.request.path}>
                    {entry.request.path}
                  </span>
                </div>
                
                {/* Timeline bar */}
                <div className="flex-1 relative h-6">
                  <div className="absolute inset-0 bg-muted rounded" />
                  <div
                    className={`absolute h-full rounded ${getStatusColor(entry.request.status_code)} opacity-80 group-hover:opacity-100 transition-opacity`}
                    style={{
                      left: `${entry.startPercent}%`,
                      width: `${entry.widthPercent}%`,
                      minWidth: '2px'
                    }}
                  >
                    <div className="absolute -top-5 left-0 text-xs opacity-0 group-hover:opacity-100 transition-opacity bg-popover px-1 rounded shadow-sm whitespace-nowrap">
                      {entry.duration.toFixed(0)}ms
                    </div>
                  </div>
                </div>
                
                {/* Status and size */}
                <div className="flex-shrink-0 flex items-center gap-2">
                  {entry.request.status_code && (
                    <Badge variant="outline" className="text-xs">
                      {entry.request.status_code}
                    </Badge>
                  )}
                  {entry.request.response_time && (
                    <span className="text-xs text-muted-foreground">
                      {entry.request.response_time.toFixed(0)}ms
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {/* Legend */}
          <div className="flex gap-4 text-xs text-muted-foreground pt-2 border-t">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500 rounded" />
              <span>2xx Success</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-blue-500 rounded" />
              <span>3xx Redirect</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-yellow-500 rounded" />
              <span>4xx Client Error</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-500 rounded" />
              <span>5xx Server Error</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}