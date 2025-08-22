import { useState, useEffect } from 'react'
import { HostList } from './components/HostList'
import { RequestList } from './components/RequestList'
import { RequestDetails } from './components/RequestDetails'
import { StatsBar } from './components/StatsBar'
import { useWebSocket } from './hooks/useWebSocket'
import { CapturedRequest, Host } from './types'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs'
import { Badge } from './components/ui/badge'
import { ScrollArea } from './components/ui/scroll-area'
import { Search, Activity } from 'lucide-react'

function App() {
  const [hosts, setHosts] = useState<Host[]>([])
  const [selectedHost, setSelectedHost] = useState<string | null>(null)
  const [requests, setRequests] = useState<CapturedRequest[]>([])
  const [selectedRequest, setSelectedRequest] = useState<string | null>(null)
  const [filterText, setFilterText] = useState('')
  const [viewMode, setViewMode] = useState<'all' | 'http' | 'rpc'>('all')
  const [stats, setStats] = useState({
    totalRequests: 0,
    rpcCalls: 0,
    avgResponseTime: 0
  })

  const { isConnected, sendMessage } = useWebSocket({
    onMessage: (data) => {
      switch (data.type) {
        case 'initial':
          const hostList = data.hosts.map((h: string) => ({ 
            name: h, 
            requestCount: 0,
            rpcCount: 0 
          }))
          setHosts(hostList)
          break
        case 'requests':
          setRequests(data.requests)
          updateStats(data.requests)
          break
        case 'new_request':
          if (data.request.host === selectedHost) {
            setRequests(prev => [data.request, ...prev])
            updateStats([data.request, ...requests])
          }
          break
      }
    }
  })

  const updateStats = (reqs: CapturedRequest[]) => {
    const rpcCount = reqs.filter(r => r.is_rpc).length
    const times = reqs.filter(r => r.response_time).map(r => r.response_time!)
    const avgTime = times.length > 0 ? times.reduce((a, b) => a + b, 0) / times.length : 0
    
    setStats({
      totalRequests: reqs.length,
      rpcCalls: rpcCount,
      avgResponseTime: avgTime
    })
  }

  const selectHost = (host: string) => {
    setSelectedHost(host)
    setSelectedRequest(null)
    sendMessage({ type: 'get_requests', host })
  }

  const filteredRequests = requests.filter(req => {
    // Filter by view mode
    if (viewMode === 'http' && req.is_rpc) return false
    if (viewMode === 'rpc' && !req.is_rpc) return false
    
    // Filter by text
    if (filterText) {
      const searchStr = filterText.toLowerCase()
      return req.path.toLowerCase().includes(searchStr) ||
             req.method.toLowerCase().includes(searchStr) ||
             (req.rpc_method && req.rpc_method.toLowerCase().includes(searchStr))
    }
    return true
  })

  useEffect(() => {
    // Fetch initial hosts on mount
    fetch('/api/hosts')
      .then(res => res.json())
      .then(data => {
        const hostList = data.hosts.map((h: string) => ({ 
          name: h, 
          requestCount: 0,
          rpcCount: 0 
        }))
        setHosts(hostList)
      })
  }, [])

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar with hosts */}
      <div className="w-64 border-r bg-sidebar">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Captured Hosts
            {isConnected && (
              <Badge variant="outline" className="ml-auto">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse" />
                Live
              </Badge>
            )}
          </h2>
        </div>
        <ScrollArea className="h-[calc(100vh-4rem)]">
          <HostList 
            hosts={hosts} 
            selectedHost={selectedHost} 
            onSelectHost={selectHost} 
          />
        </ScrollArea>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Stats bar */}
        <StatsBar 
          selectedHost={selectedHost}
          totalRequests={stats.totalRequests}
          rpcCalls={stats.rpcCalls}
          avgResponseTime={stats.avgResponseTime}
        />

        {/* Content area */}
        <div className="flex-1 flex">
          {/* Request list */}
          <div className="w-1/2 border-r flex flex-col">
            <div className="p-4 border-b space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input
                  type="search"
                  placeholder="Filter requests..."
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
                  className="pl-9"
                />
              </div>
              
              <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as any)}>
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="http">HTTP</TabsTrigger>
                  <TabsTrigger value="rpc">RPC</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            <ScrollArea className="flex-1">
              <RequestList
                requests={filteredRequests}
                selectedRequest={selectedRequest}
                onSelectRequest={setSelectedRequest}
              />
            </ScrollArea>
          </div>

          {/* Request details */}
          <div className="w-1/2">
            {selectedRequest ? (
              <RequestDetails requestId={selectedRequest} />
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                Select a request to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App