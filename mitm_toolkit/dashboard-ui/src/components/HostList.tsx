import { useState, useMemo } from 'react'
import { Host } from '../types'
import { cn } from '../lib/utils'
import { Badge } from './ui/badge'
import { Input } from './ui/input'
import { Server, Search } from 'lucide-react'

interface HostListProps {
  hosts: Host[]
  selectedHost: string | null
  onSelectHost: (host: string) => void
}

export function HostList({ hosts, selectedHost, onSelectHost }: HostListProps) {
  const [searchQuery, setSearchQuery] = useState('')
  
  // Filter hosts based on search query
  const filteredHosts = useMemo(() => {
    if (!searchQuery) return hosts
    
    const query = searchQuery.toLowerCase()
    return hosts.filter(host => 
      host.name.toLowerCase().includes(query)
    )
  }, [hosts, searchQuery])
  
  // Handle escape key to clear search
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setSearchQuery('')
    }
  }
  
  return (
    <div className="flex flex-col h-full">
      {/* Search input */}
      <div className="p-2 border-b space-y-2">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            type="search"
            placeholder="Search hosts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pl-8 h-8 text-sm"
          />
        </div>
        {searchQuery && (
          <div className="text-xs text-muted-foreground">
            Found {filteredHosts.length} of {hosts.length} hosts
          </div>
        )}
      </div>
      
      {/* Host list */}
      <div className="p-2 flex-1 overflow-y-auto">
        {filteredHosts.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            {searchQuery ? 'No hosts match your search' : 'No hosts captured yet'}
          </div>
        ) : (
          filteredHosts.map((host) => (
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
    </div>
  )
}