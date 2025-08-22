import { CapturedRequest } from '../types'
import { cn } from '../lib/utils'
import { Badge } from './ui/badge'
import { format } from 'date-fns'
import { Clock, Hash } from 'lucide-react'

interface RequestListProps {
  requests: CapturedRequest[]
  selectedRequest: string | null
  onSelectRequest: (id: string) => void
}

const methodColors: Record<string, string> = {
  GET: 'bg-green-500',
  POST: 'bg-blue-500',
  PUT: 'bg-orange-500',
  DELETE: 'bg-red-500',
  PATCH: 'bg-purple-500',
  HEAD: 'bg-gray-500',
  OPTIONS: 'bg-gray-500',
}

const rpcTypeColors: Record<string, string> = {
  'json-rpc': 'bg-teal-600',
  'grpc': 'bg-blue-600',
  'soap': 'bg-purple-600',
  'xml-rpc': 'bg-orange-600',
}

export function RequestList({ requests, selectedRequest, onSelectRequest }: RequestListProps) {
  if (requests.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No requests captured
      </div>
    )
  }

  return (
    <div className="p-2">
      {requests.map((request) => {
        const statusClass = request.status_code 
          ? request.status_code >= 200 && request.status_code < 300 
            ? 'text-green-600 dark:text-green-400' 
            : 'text-red-600 dark:text-red-400'
          : ''
        
        const displayPath = request.is_rpc && request.rpc_method 
          ? request.rpc_method 
          : request.path

        return (
          <div
            key={request.id}
            onClick={() => onSelectRequest(request.id)}
            className={cn(
              "p-3 rounded-lg mb-2 cursor-pointer transition-all",
              "border hover:bg-accent",
              selectedRequest === request.id && "bg-accent border-primary",
              request.is_rpc && "border-l-4 border-l-teal-600"
            )}
          >
            {/* First row: Method, RPC badge, Path/Method, Status */}
            <div className="flex items-center gap-2 mb-2">
              <Badge 
                variant="secondary" 
                className={cn(
                  "text-xs font-bold text-white",
                  methodColors[request.method] || 'bg-gray-500'
                )}
              >
                {request.method}
              </Badge>
              
              {request.is_rpc && request.rpc_type && (
                <Badge 
                  variant="secondary"
                  className={cn(
                    "text-xs text-white",
                    rpcTypeColors[request.rpc_type] || 'bg-gray-600'
                  )}
                >
                  {request.rpc_type.toUpperCase()}
                  {request.rpc_batch && ' (batch)'}
                </Badge>
              )}
              
              <span className="flex-1 font-mono text-sm truncate">
                {displayPath}
              </span>
              
              {request.status_code && (
                <span className={cn("text-sm font-semibold", statusClass)}>
                  {request.status_code}
                </span>
              )}
            </div>

            {/* Second row: Request ID, Timestamp, Response time */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Hash className="w-3 h-3" />
                <span className="font-mono">{request.id.substring(0, 8)}</span>
              </div>
              
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{format(new Date(request.timestamp), 'HH:mm:ss')}</span>
              </div>
              
              {request.response_time && (
                <span className="ml-auto">
                  {request.response_time.toFixed(0)}ms
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}