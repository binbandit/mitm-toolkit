import { useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Progress } from './ui/progress'
import { Activity, Clock, TrendingUp, AlertTriangle } from 'lucide-react'
import { CapturedRequest } from '../types'

interface PerformanceMetricsProps {
  requests: CapturedRequest[]
}

export function PerformanceMetrics({ requests }: PerformanceMetricsProps) {
  const metrics = useMemo(() => {
    if (requests.length === 0) {
      return {
        avgResponseTime: 0,
        p95ResponseTime: 0,
        p99ResponseTime: 0,
        slowestRequest: null,
        fastestRequest: null,
        errorRate: 0,
        successRate: 100,
        totalRequests: 0,
        methodBreakdown: {},
        statusBreakdown: {}
      }
    }
    
    // Get response times
    const responseTimes = requests
      .filter(r => r.response_time !== undefined && r.response_time !== null)
      .map(r => r.response_time!)
      .sort((a, b) => a - b)
    
    // Calculate percentiles
    const p95Index = Math.floor(responseTimes.length * 0.95)
    const p99Index = Math.floor(responseTimes.length * 0.99)
    
    // Calculate error rate
    const errors = requests.filter(r => r.status_code && r.status_code >= 400).length
    const errorRate = (errors / requests.length) * 100
    
    // Method breakdown
    const methodBreakdown = requests.reduce((acc, req) => {
      acc[req.method] = (acc[req.method] || 0) + 1
      return acc
    }, {} as Record<string, number>)
    
    // Status code breakdown
    const statusBreakdown = requests.reduce((acc, req) => {
      if (req.status_code) {
        const category = `${Math.floor(req.status_code / 100)}xx`
        acc[category] = (acc[category] || 0) + 1
      }
      return acc
    }, {} as Record<string, number>)
    
    // Find slowest and fastest
    const sortedByTime = [...requests]
      .filter(r => r.response_time)
      .sort((a, b) => (b.response_time || 0) - (a.response_time || 0))
    
    return {
      avgResponseTime: responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length || 0,
      p95ResponseTime: responseTimes[p95Index] || 0,
      p99ResponseTime: responseTimes[p99Index] || 0,
      slowestRequest: sortedByTime[0] || null,
      fastestRequest: sortedByTime[sortedByTime.length - 1] || null,
      errorRate,
      successRate: 100 - errorRate,
      totalRequests: requests.length,
      methodBreakdown,
      statusBreakdown
    }
  }, [requests])
  
  const getPerformanceColor = (time: number) => {
    if (time < 100) return 'text-green-500'
    if (time < 500) return 'text-yellow-500'
    if (time < 1000) return 'text-orange-500'
    return 'text-red-500'
  }
  
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {/* Response Time Metrics */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Response Times</CardTitle>
          <CardDescription className="text-xs">Performance percentiles</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Average</span>
              <span className={`text-sm font-medium ${getPerformanceColor(metrics.avgResponseTime)}`}>
                {metrics.avgResponseTime.toFixed(1)}ms
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">P95</span>
              <span className={`text-sm font-medium ${getPerformanceColor(metrics.p95ResponseTime)}`}>
                {metrics.p95ResponseTime.toFixed(1)}ms
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">P99</span>
              <span className={`text-sm font-medium ${getPerformanceColor(metrics.p99ResponseTime)}`}>
                {metrics.p99ResponseTime.toFixed(1)}ms
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Success/Error Rate */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
          <CardDescription className="text-xs">Request success vs errors</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl font-bold">{metrics.successRate.toFixed(1)}%</span>
              {metrics.errorRate > 10 && (
                <AlertTriangle className="w-4 h-4 text-yellow-500" />
              )}
            </div>
            <Progress value={metrics.successRate} className="h-2" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Success: {metrics.totalRequests - Math.round(metrics.totalRequests * metrics.errorRate / 100)}</span>
              <span>Errors: {Math.round(metrics.totalRequests * metrics.errorRate / 100)}</span>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Method Breakdown */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">HTTP Methods</CardTitle>
          <CardDescription className="text-xs">Request method distribution</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(metrics.methodBreakdown).map(([method, count]) => (
              <div key={method} className="flex items-center justify-between">
                <Badge variant="outline" className="text-xs">
                  {method}
                </Badge>
                <span className="text-sm font-medium">{count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      
      {/* Status Code Distribution */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Status Codes</CardTitle>
          <CardDescription className="text-xs">Response status distribution</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(metrics.statusBreakdown).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between">
                <Badge 
                  variant={status.startsWith('2') ? 'default' : status.startsWith('4') ? 'destructive' : 'secondary'}
                  className="text-xs"
                >
                  {status}
                </Badge>
                <span className="text-sm font-medium">{count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      
      {/* Slowest Request */}
      {metrics.slowestRequest && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Slowest Request</CardTitle>
            <CardDescription className="text-xs">Highest response time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-red-500" />
                <span className="text-lg font-bold text-red-500">
                  {metrics.slowestRequest.response_time?.toFixed(0)}ms
                </span>
              </div>
              <div className="text-xs text-muted-foreground truncate">
                {metrics.slowestRequest.method} {metrics.slowestRequest.path}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Fastest Request */}
      {metrics.fastestRequest && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Fastest Request</CardTitle>
            <CardDescription className="text-xs">Lowest response time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                <span className="text-lg font-bold text-green-500">
                  {metrics.fastestRequest.response_time?.toFixed(0)}ms
                </span>
              </div>
              <div className="text-xs text-muted-foreground truncate">
                {metrics.fastestRequest.method} {metrics.fastestRequest.path}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}