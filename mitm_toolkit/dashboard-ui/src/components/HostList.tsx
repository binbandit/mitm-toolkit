import { Host } from '../types'
import { cn } from '../lib/utils'
import { Badge } from './ui/badge'
import { Server } from 'lucide-react'

interface HostListProps {
  hosts: Host[]
  selectedHost: string | null
  onSelectHost: (host: string) => void
}

export function HostList({ hosts, selectedHost, onSelectHost }: HostListProps) {
  return (
    <div className="p-2">
      {hosts.length === 0 ? (
        <div className="text-center text-muted-foreground py-8">
          No hosts captured yet
        </div>
      ) : (
        hosts.map((host) => (
          <button
            key={host.name}
            onClick={() => onSelectHost(host.name)}
            className={cn(
              "w-full text-left p-3 rounded-lg mb-1 transition-colors",
              "hover:bg-sidebar-accent",
              selectedHost === host.name && "bg-sidebar-accent"
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-muted-foreground" />
                <span className="font-medium text-sm">{host.name}</span>
              </div>
              {host.requestCount > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {host.requestCount}
                </Badge>
              )}
            </div>
            {host.rpcCount !== undefined && host.rpcCount > 0 && (
              <div className="mt-1">
                <Badge variant="outline" className="text-xs">
                  {host.rpcCount} RPC
                </Badge>
              </div>
            )}
          </button>
        ))
      )}
    </div>
  )
}