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
import { Search, Activity, BarChart, Clock } from 'lucide-react'
import { Toaster } from './components/ui/sonner'

function App() {
  const [hosts, setHosts] = useState<Host[]>([])
  const [selectedHost, setSelectedHost] = useState<string | null>(null)
  const [requests, setRequests] = useState<CapturedRequest[]>([])
  const [selectedRequest, setSelectedRequest] = useState<string | null>(null)
  const [filterText, setFilterText] = useState('')
  const [viewMode, setViewMode] = useState<'all' | 'http' | 'rpc'>('all')
  const [activeTab, setActiveTab] = useState<'requests' | 'performance' | 'timeline'>('requests')
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
      <div className="w-64 flex-shrink-0 border-r bg-sidebar">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Captured Hosts
            {isConnected && (
              <Badge variant="outline" className="ml-2">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse" />
                Live
              </Badge>
            )}
          </h2>
          <div className="flex items-center gap-1">
            <KeyboardShortcuts />
            <Settings />
          </div>
        </div>
        <div className="h-[calc(100vh-3.25rem)]">
          <HostList 
            hosts={hosts} 
            selectedHost={selectedHost} 
            onSelectHost={selectHost} 
          />
        </div>
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
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="flex-1 flex flex-col">
            <div className="border-b px-4">
              <TabsList className="h-12">
                <TabsTrigger value="requests" className="flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Requests
                </TabsTrigger>
                <TabsTrigger value="timeline" className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  Timeline
                </TabsTrigger>
                <TabsTrigger value="performance" className="flex items-center gap-2">
                  <BarChart className="w-4 h-4" />
                  Analytics
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="requests" className="flex-1 flex m-0">
              {/* Request list */}
              <div className="w-1/2 border-r flex flex-col">
                <div className="p-4 border-b space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                      <Input
                        ref={searchInputRef}
                        type="search"
                        placeholder="Filter requests..."
                        value={filterText}
                        onChange={(e) => setFilterText(e.target.value)}
                        className="pl-9"
                      />
                    </div>
                    <HarExport 
                      requests={filteredRequests}
                      onImport={(imported) => setRequests(prev => [...imported, ...prev])}
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
            </TabsContent>

            <TabsContent value="timeline" className="flex-1 p-6 m-0 overflow-auto">
              <div className="max-w-7xl mx-auto">
                <h2 className="text-2xl font-bold mb-6">Request Timeline</h2>
                <TimelineView 
                  requests={filteredRequests}
                  onSelectRequest={setSelectedRequest}
                  selectedRequest={selectedRequest}
                />
              </div>
            </TabsContent>

            <TabsContent value="performance" className="flex-1 p-6 m-0 overflow-auto">
              <div className="max-w-7xl mx-auto">
                <h2 className="text-2xl font-bold mb-6">Performance Analytics</h2>
                {requests.length > 0 ? (
                  <PerformanceMetrics requests={requests} />
                ) : (
                  <div className="flex items-center justify-center h-64 text-muted-foreground">
                    <div className="text-center">
                      <BarChart className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No request data available</p>
                      <p className="text-sm mt-2">Select a host to view performance metrics</p>
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
    </>
  )
}

export default App