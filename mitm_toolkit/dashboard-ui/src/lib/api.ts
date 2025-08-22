// API configuration
// Allow users to specify custom backend URL via localStorage
const getApiBaseUrl = () => {
  // Check if user has set a custom backend URL
  const customUrl = localStorage.getItem('MITM_BACKEND_URL')
  if (customUrl) return customUrl
  
  // In development, use localhost
  if (import.meta.env.DEV) return 'http://localhost:8000'
  
  // In production (including GitHub Pages), default to localhost
  // Users can connect to their local instance
  return 'http://localhost:8000'
}

const API_BASE_URL = getApiBaseUrl()

export async function fetchAPI(endpoint: string, options?: RequestInit) {
  const url = `${API_BASE_URL}${endpoint}`
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }
  
  return response.json()
}

export const api = {
  getHosts: () => fetchAPI('/api/hosts'),
  getRequests: (host: string, limit = 100) => 
    fetchAPI(`/api/requests/${host}?limit=${limit}`),
  getRequestDetail: (requestId: string) => 
    fetchAPI(`/api/request/${requestId}`),
  getRPCCalls: (host: string) => 
    fetchAPI(`/api/rpc/${host}`),
  getEndpointVariations: (host: string, path: string, method = 'GET') =>
    fetchAPI(`/api/endpoint-variations/${host}/${path}?method=${method}`),
}