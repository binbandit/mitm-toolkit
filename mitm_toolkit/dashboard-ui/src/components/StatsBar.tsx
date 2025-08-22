import { Card } from './ui/card'
import { Activity, Globe, Zap } from 'lucide-react'

interface StatsBarProps {
  selectedHost: string | null
  totalRequests: number
  rpcCalls: number
  avgResponseTime: number
}

export function StatsBar({ selectedHost, totalRequests, rpcCalls, avgResponseTime }: StatsBarProps) {
  return (
    <div className="p-4 border-b bg-muted/50">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">MITM Toolkit Dashboard</h1>
          {selectedHost && (
            <p className="text-sm text-muted-foreground">
              Monitoring: <span className="font-mono">{selectedHost}</span>
            </p>
          )}
        </div>
        
        <div className="flex gap-4">
          <Card className="px-4 py-2">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-500" />
              <div>
                <p className="text-xs text-muted-foreground">Total Requests</p>
                <p className="text-xl font-bold">{totalRequests}</p>
              </div>
            </div>
          </Card>
          
          <Card className="px-4 py-2">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-green-500" />
              <div>
                <p className="text-xs text-muted-foreground">RPC Calls</p>
                <p className="text-xl font-bold">{rpcCalls}</p>
              </div>
            </div>
          </Card>
          
          <Card className="px-4 py-2">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-500" />
              <div>
                <p className="text-xs text-muted-foreground">Avg Response</p>
                <p className="text-xl font-bold">{avgResponseTime.toFixed(0)}ms</p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}