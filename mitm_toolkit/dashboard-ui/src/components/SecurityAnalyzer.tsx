import { useMemo } from 'react'
import { CapturedRequest, CapturedResponse } from '../types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Alert, AlertDescription, AlertTitle } from './ui/alert'
import { Shield, ShieldAlert, ShieldCheck, ShieldX, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

interface SecurityAnalyzerProps {
  request: CapturedRequest
  response: CapturedResponse | null
}

interface SecurityIssue {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description: string
  recommendation: string
}

export function SecurityAnalyzer({ request, response }: SecurityAnalyzerProps) {
  const analysis = useMemo(() => {
    const issues: SecurityIssue[] = []
    const goodPractices: string[] = []
    
    if (!response || !response.headers) {
      return { issues, goodPractices, score: 0 }
    }
    
    const headers = response.headers
    const headersLower = Object.keys(headers).reduce((acc, key) => {
      acc[key.toLowerCase()] = headers[key]
      return acc
    }, {} as Record<string, string>)
    
    // Check for HTTPS
    const isHttps = request.url.startsWith('https://')
    if (!isHttps) {
      issues.push({
        severity: 'critical',
        title: 'No HTTPS',
        description: 'The connection is not encrypted',
        recommendation: 'Always use HTTPS for sensitive data transmission'
      })
    } else {
      goodPractices.push('HTTPS enabled')
    }
    
    // Check Strict-Transport-Security
    if (!headersLower['strict-transport-security']) {
      issues.push({
        severity: 'high',
        title: 'Missing Strict-Transport-Security',
        description: 'HSTS header is not set',
        recommendation: 'Add: Strict-Transport-Security: max-age=31536000; includeSubDomains'
      })
    } else {
      const hsts = headersLower['strict-transport-security']
      goodPractices.push('HSTS enabled')
      if (!hsts.includes('includeSubDomains')) {
        issues.push({
          severity: 'medium',
          title: 'HSTS without includeSubDomains',
          description: 'Subdomains are not protected by HSTS',
          recommendation: 'Add includeSubDomains to HSTS header'
        })
      }
    }
    
    // Check X-Content-Type-Options
    if (!headersLower['x-content-type-options']) {
      issues.push({
        severity: 'medium',
        title: 'Missing X-Content-Type-Options',
        description: 'MIME type sniffing not prevented',
        recommendation: 'Add: X-Content-Type-Options: nosniff'
      })
    } else if (headersLower['x-content-type-options'] === 'nosniff') {
      goodPractices.push('MIME sniffing prevention')
    }
    
    // Check X-Frame-Options
    if (!headersLower['x-frame-options'] && !headersLower['content-security-policy']?.includes('frame-ancestors')) {
      issues.push({
        severity: 'medium',
        title: 'Missing X-Frame-Options',
        description: 'Clickjacking protection not enabled',
        recommendation: 'Add: X-Frame-Options: DENY or SAMEORIGIN'
      })
    } else {
      goodPractices.push('Clickjacking protection')
    }
    
    // Check Content-Security-Policy
    if (!headersLower['content-security-policy']) {
      issues.push({
        severity: 'high',
        title: 'Missing Content-Security-Policy',
        description: 'No CSP header to prevent XSS attacks',
        recommendation: 'Implement a Content-Security-Policy header'
      })
    } else {
      goodPractices.push('CSP implemented')
      const csp = headersLower['content-security-policy']
      if (csp.includes('unsafe-inline') || csp.includes('unsafe-eval')) {
        issues.push({
          severity: 'medium',
          title: 'Weak CSP Configuration',
          description: 'CSP allows unsafe inline scripts or eval',
          recommendation: 'Remove unsafe-inline and unsafe-eval from CSP'
        })
      }
    }
    
    // Check X-XSS-Protection
    if (!headersLower['x-xss-protection']) {
      issues.push({
        severity: 'low',
        title: 'Missing X-XSS-Protection',
        description: 'Browser XSS filter not enabled',
        recommendation: 'Add: X-XSS-Protection: 1; mode=block'
      })
    } else if (headersLower['x-xss-protection'] === '0') {
      issues.push({
        severity: 'medium',
        title: 'XSS Protection Disabled',
        description: 'Browser XSS filter is explicitly disabled',
        recommendation: 'Enable XSS protection: X-XSS-Protection: 1; mode=block'
      })
    } else {
      goodPractices.push('XSS filter enabled')
    }
    
    // Check Referrer-Policy
    if (!headersLower['referrer-policy']) {
      issues.push({
        severity: 'low',
        title: 'Missing Referrer-Policy',
        description: 'Referrer information may leak',
        recommendation: 'Add: Referrer-Policy: strict-origin-when-cross-origin'
      })
    } else {
      goodPractices.push('Referrer policy set')
    }
    
    // Check Permissions-Policy
    if (!headersLower['permissions-policy']) {
      issues.push({
        severity: 'info',
        title: 'Missing Permissions-Policy',
        description: 'Browser features not explicitly controlled',
        recommendation: 'Consider adding Permissions-Policy header'
      })
    } else {
      goodPractices.push('Permissions policy set')
    }
    
    // Check for sensitive data in URL
    if (request.query_params) {
      const sensitiveParams = ['password', 'token', 'api_key', 'secret', 'auth']
      const foundSensitive = Object.keys(request.query_params).filter(key => 
        sensitiveParams.some(sensitive => key.toLowerCase().includes(sensitive))
      )
      if (foundSensitive.length > 0) {
        issues.push({
          severity: 'critical',
          title: 'Sensitive Data in URL',
          description: `Potentially sensitive parameters in URL: ${foundSensitive.join(', ')}`,
          recommendation: 'Never send sensitive data in URL parameters'
        })
      }
    }
    
    // Check cookies
    const setCookie = headersLower['set-cookie']
    if (setCookie) {
      if (!setCookie.includes('Secure')) {
        issues.push({
          severity: 'high',
          title: 'Cookie without Secure flag',
          description: 'Cookies can be transmitted over unencrypted connections',
          recommendation: 'Add Secure flag to all cookies'
        })
      }
      if (!setCookie.includes('HttpOnly')) {
        issues.push({
          severity: 'high',
          title: 'Cookie without HttpOnly flag',
          description: 'Cookies are accessible via JavaScript',
          recommendation: 'Add HttpOnly flag to prevent XSS attacks'
        })
      }
      if (!setCookie.includes('SameSite')) {
        issues.push({
          severity: 'medium',
          title: 'Cookie without SameSite attribute',
          description: 'Cookies vulnerable to CSRF attacks',
          recommendation: 'Add SameSite=Strict or SameSite=Lax'
        })
      }
    }
    
    // Calculate security score
    const maxScore = 100
    const criticalPenalty = 25
    const highPenalty = 15
    const mediumPenalty = 10
    const lowPenalty = 5
    
    let score = maxScore
    issues.forEach(issue => {
      switch (issue.severity) {
        case 'critical': score -= criticalPenalty; break
        case 'high': score -= highPenalty; break
        case 'medium': score -= mediumPenalty; break
        case 'low': score -= lowPenalty; break
      }
    })
    
    return {
      issues,
      goodPractices,
      score: Math.max(0, score)
    }
  }, [request, response])
  
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <ShieldX className="w-4 h-4" />
      case 'high': return <ShieldAlert className="w-4 h-4" />
      case 'medium': return <AlertTriangle className="w-4 h-4" />
      default: return <Shield className="w-4 h-4" />
    }
  }
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'destructive'
      case 'high': return 'destructive'
      case 'medium': return 'secondary'
      case 'low': return 'outline'
      default: return 'outline'
    }
  }
  
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    if (score >= 40) return 'text-orange-600'
    return 'text-red-600'
  }
  
  const getScoreIcon = (score: number) => {
    if (score >= 80) return <ShieldCheck className="w-8 h-8 text-green-600" />
    if (score >= 60) return <Shield className="w-8 h-8 text-yellow-600" />
    if (score >= 40) return <ShieldAlert className="w-8 h-8 text-orange-600" />
    return <ShieldX className="w-8 h-8 text-red-600" />
  }
  
  if (!response) {
    return (
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>No Response</AlertTitle>
        <AlertDescription>
          Security analysis requires a response to analyze
        </AlertDescription>
      </Alert>
    )
  }
  
  return (
    <div className="space-y-4">
      {/* Security Score */}
      <Card>
        <CardHeader>
          <CardTitle>Security Score</CardTitle>
          <CardDescription>Overall security assessment</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {getScoreIcon(analysis.score)}
              <div>
                <div className={`text-3xl font-bold ${getScoreColor(analysis.score)}`}>
                  {analysis.score}/100
                </div>
                <p className="text-sm text-muted-foreground">
                  {analysis.issues.length} issues found
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium">
                {analysis.issues.filter(i => i.severity === 'critical').length} Critical
              </p>
              <p className="text-sm font-medium">
                {analysis.issues.filter(i => i.severity === 'high').length} High
              </p>
              <p className="text-sm font-medium">
                {analysis.issues.filter(i => i.severity === 'medium').length} Medium
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Security Issues */}
      {analysis.issues.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Security Issues</CardTitle>
            <CardDescription>Headers and configurations that need attention</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {analysis.issues.map((issue, index) => (
              <Alert key={index} className="relative">
                <div className="flex items-start gap-2">
                  {getSeverityIcon(issue.severity)}
                  <div className="flex-1">
                    <AlertTitle className="flex items-center gap-2">
                      {issue.title}
                      <Badge variant={getSeverityColor(issue.severity)}>
                        {issue.severity}
                      </Badge>
                    </AlertTitle>
                    <AlertDescription className="mt-2 space-y-2">
                      <p>{issue.description}</p>
                      <p className="text-xs font-mono bg-muted p-2 rounded">
                        {issue.recommendation}
                      </p>
                    </AlertDescription>
                  </div>
                </div>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}
      
      {/* Good Practices */}
      {analysis.goodPractices.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Good Practices</CardTitle>
            <CardDescription>Security measures properly implemented</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {analysis.goodPractices.map((practice, index) => (
                <div key={index} className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">{practice}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}