export interface CapturedRequest {
  id: string
  timestamp: string
  method: string
  url: string
  path: string
  host: string
  status_code?: number
  response_time?: number
  is_rpc: boolean
  rpc_type?: string
  rpc_method?: string
  rpc_batch?: boolean
  query_params?: Record<string, any>
  headers?: Record<string, string>
  body?: string
  body_decoded?: string
}

export interface CapturedResponse {
  status_code: number
  headers: Record<string, string>
  body?: string
  body_decoded?: string
  response_time: number
}

export interface RequestDetail {
  request: CapturedRequest
  response?: CapturedResponse
}

export interface Host {
  name: string
  requestCount: number
  rpcCount?: number
}

export interface RPCCall {
  id: string
  timestamp: string
  type: string
  method: string
  batch: boolean
  batch_count: number
  url: string
  status_code?: number
  response_time?: number
}

export type ViewMode = 'all' | 'http' | 'rpc'
export type TabType = 'request' | 'response' | 'headers'