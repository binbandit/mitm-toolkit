import { useState, useEffect, useRef } from 'react'
import { HostList } from './components/HostList'
import { RequestList } from './components/RequestList'
import { RequestDetails } from './components/RequestDetails'
import { StatsBar } from './components/StatsBar'
import { Settings } from './components/Settings'
import { PerformanceMetrics } from './components/PerformanceMetrics'
import { KeyboardShortcuts } from './components/KeyboardShortcuts'
import { HarExport } from './components/HarExport'
import { TimelineView } from './components/TimelineView'
import { useWebSocket } from './hooks/useWebSocket'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { CapturedRequest, Host } from './types'
import { api } from './lib/api'
import { Input } from './components/ui/input'
import { Tabs, TabsList, TabsTrigger, TabsContent } from './components/ui/tabs'
import { Badge } from './components/ui/badge'
import { ScrollArea } from './components/ui/scroll-area'
import { Search, Activity, BarChart, Clock, Filter, Globe } from 'lucide-react'
import { Toaster } from './components/ui/sonner'
import { Button } from './components/ui/button'
import { cn } from './lib/utils'

function App() {
  const [hosts, setHosts] = useState<Host[]>([])
  const [selectedHost, setSelectedHost] = useState<string | null>(null)
  const [requests, setRequests] = useState<CapturedRequest[]>([])
  const [selectedRequest, setSelectedRequest] = useState<string | null>(null)
  const [filterText, setFilterText] = useState('')
  const [viewMode, setViewMode] = useState<'all' | 'http' | 'rpc'>('all')
  const [activeTab, setActiveTab] = useState<'requests' | 'performance' | 'timeline'>('requests')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [stats, setStats] = useState({
    totalRequests: 0,
    rpcCalls: 0,
    avgResponseTime: 0
  })
  const searchInputRef = useRef<HTMLInputElement>(null)

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

  // Keyboard shortcuts handlers
  const handleSearch = () => {
    searchInputRef.current?.focus()
  }

  const handleClearFilters = () => {
    setFilterText('')
    setViewMode('all')
  }

  const handleRefresh = () => {
    if (selectedHost) {
      sendMessage({ type: 'get_requests', host: selectedHost })
    } else {
      api.getHosts()
        .then((data: any) => {
          const hostList = data.hosts.map((h: string) => ({ 
            name: h, 
            requestCount: 0,
            rpcCount: 0 
          }))
          setHosts(hostList)
        })
    }
  }

  const handleSelectNext = () => {
    if (filteredRequests.length === 0) return
    const currentIndex = selectedRequest ? 
      filteredRequests.findIndex(r => r.id === selectedRequest) : -1
    const nextIndex = (currentIndex + 1) % filteredRequests.length
    setSelectedRequest(filteredRequests[nextIndex].id)
  }

  const handleSelectPrevious = () => {
    if (filteredRequests.length === 0) return
    const currentIndex = selectedRequest ? 
      filteredRequests.findIndex(r => r.id === selectedRequest) : 0
    const prevIndex = currentIndex > 0 ? currentIndex - 1 : filteredRequests.length - 1
    setSelectedRequest(filteredRequests[prevIndex].id)
  }

  // Initialize keyboard shortcuts
  useKeyboardShortcuts({
    onSearch: handleSearch,
    onClearFilters: handleClearFilters,
    onRefresh: handleRefresh,
    onSelectNext: handleSelectNext,
    onSelectPrevious: handleSelectPrevious
  })

  useEffect(() => {
    // Fetch initial hosts on mount
    api.getHosts()
      .then((data: any) => {
        const hostList = data.hosts.map((h: string) => ({ 
          name: h, 
          requestCount: 0,
          rpcCount: 0 
        }))
        setHosts(hostList)
      })
      .catch((err: any) => {
        console.error('Failed to fetch hosts:', err)
      })
  }, [])

  return (
    <>
      <Toaster position="bottom-right" />
      <div className="flex h-screen bg-background">
        
        {/* Sidebar with hosts */}
        <div className={cn(
          "border-r bg-card transition-all duration-200",
          sidebarCollapsed ? "w-16" : "w-64"
        )}>
          <div className="h-full flex flex-col">
            {/* Sidebar header */}
            <div className="px-3 py-2 border-b flex items-center justify-between h-12">
              {!sidebarCollapsed && (
                <h2 className="text-sm font-semibold flex items-center gap-2">
                  <Globe className="w-4 h-4" />
                  Hosts
                  {isConnected && (
                    <Badge variant="outline" className="text-xs px-1 py-0">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1 animate-pulse" />
                      Live
                    </Badge>
                  )}
                </h2>
              )}
              <div className="flex items-center gap-1">
                {!sidebarCollapsed && <KeyboardShortcuts />}
                {!sidebarCollapsed && <Settings />}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                >
                  <Activity className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            {/* Hosts list */}
            <div className="flex-1 overflow-hidden">
              {!sidebarCollapsed && (
                <HostList 
                  hosts={hosts} 
                  selectedHost={selectedHost} 
                  onSelectHost={selectHost} 
                />
              )}
            </div>
          </div>
        </div>

        {/* Main content area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top stats bar */}
          {selectedHost && (
            <div className="border-b bg-card/50">
              <StatsBar 
                selectedHost={selectedHost}
                totalRequests={stats.totalRequests}
                rpcCalls={stats.rpcCalls}
                avgResponseTime={stats.avgResponseTime}
              />
            </div>
          )}

          {/* Main tabs */}
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="flex-1 flex flex-col">
            <div className="border-b px-4 bg-card/30">
              <TabsList className="h-10">
                <TabsTrigger value="requests" className="text-xs">
                  <Activity className="w-3 h-3 mr-1" />
                  Requests
                </TabsTrigger>
                <TabsTrigger value="timeline" className="text-xs">
                  <Clock className="w-3 h-3 mr-1" />
                  Timeline
                </TabsTrigger>
                <TabsTrigger value="performance" className="text-xs">
                  <BarChart className="w-3 h-3 mr-1" />
                  Analytics
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Requests tab */}
            <TabsContent value="requests" className="flex-1 flex m-0">
              <div className="flex w-full h-full">
                {/* Request list panel */}
                <div className="w-[450px] border-r flex flex-col bg-muted/5">
                  {/* Filters */}
                  <div className="p-3 border-b space-y-2 bg-card/50">
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1">
                        <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 text-muted-foreground w-3.5 h-3.5" />
                        <Input
                          ref={searchInputRef}
                          type="search"
                          placeholder="Filter requests..."
                          value={filterText}
                          onChange={(e) => setFilterText(e.target.value)}
                          className="pl-8 h-8 text-xs"
                        />
                      </div>
                      <HarExport 
                        requests={filteredRequests}
                        onImport={(imported) => setRequests(prev => [...imported, ...prev])}
                      />
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Filter className="w-3 h-3 text-muted-foreground" />
                      <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as any)} className="flex-1">
                        <TabsList className="grid w-full grid-cols-3 h-7">
                          <TabsTrigger value="all" className="text-xs">All</TabsTrigger>
                          <TabsTrigger value="http" className="text-xs">HTTP</TabsTrigger>
                          <TabsTrigger value="rpc" className="text-xs">RPC</TabsTrigger>
                        </TabsList>
                      </Tabs>
                    </div>
                  </div>

                  {/* Request list */}
                  <ScrollArea className="flex-1">
                    <RequestList
                      requests={filteredRequests}
                      selectedRequest={selectedRequest}
                      onSelectRequest={setSelectedRequest}
                    />
                  </ScrollArea>
                </div>

                {/* Request details panel */}
                <div className="flex-1 overflow-hidden">
                  {selectedRequest ? (
                    <RequestDetails requestId={selectedRequest} />
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      <div className="text-center space-y-3">
                        <Activity className="w-12 h-12 mx-auto opacity-20" />
                        <div>
                          <p className="font-medium">No request selected</p>
                          <p className="text-xs mt-1">Select a request from the list to view details</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Timeline tab */}
            <TabsContent value="timeline" className="flex-1 p-4 m-0 overflow-auto">
              <div className="max-w-6xl mx-auto">
                <TimelineView 
                  requests={filteredRequests}
                  onSelectRequest={setSelectedRequest}
                  selectedRequest={selectedRequest}
                />
              </div>
            </TabsContent>

            {/* Performance tab */}
            <TabsContent value="performance" className="flex-1 p-4 m-0 overflow-auto">
              <div className="max-w-6xl mx-auto">
                {requests.length > 0 ? (
                  <PerformanceMetrics requests={requests} />
                ) : (
                  <div className="flex items-center justify-center h-64 text-muted-foreground">
                    <div className="text-center">
                      <BarChart className="w-12 h-12 mx-auto mb-4 opacity-20" />
                      <p className="font-medium">No data available</p>
                      <p className="text-xs mt-1">Select a host to view performance metrics</p>
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </>
  )
}

export default App