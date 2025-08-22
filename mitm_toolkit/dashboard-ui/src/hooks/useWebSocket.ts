import { useEffect, useRef, useState, useCallback } from 'react'

interface UseWebSocketOptions {
  onMessage?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectInterval?: number
  autoReconnect?: boolean
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    reconnectInterval = 5000,
    autoReconnect = true
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const mountedRef = useRef(true)
  const isConnectingRef = useRef(false)

  // Store callbacks in refs to avoid recreating functions
  const onMessageRef = useRef(onMessage)
  const onConnectRef = useRef(onConnect)
  const onDisconnectRef = useRef(onDisconnect)

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage
    onConnectRef.current = onConnect
    onDisconnectRef.current = onDisconnect
  }, [onMessage, onConnect, onDisconnect])

  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current || !mountedRef.current) {
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }

    isConnectingRef.current = true

    // Clear any existing connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    // Get WebSocket URL based on environment and user configuration
    const getWsUrl = () => {
      // Check for custom backend URL
      const customUrl = localStorage.getItem('MITM_BACKEND_URL')
      if (customUrl) {
        const wsProtocol = customUrl.startsWith('https') ? 'wss:' : 'ws:'
        const host = customUrl.replace(/^https?:\/\//, '')
        return `${wsProtocol}//${host}/ws`
      }
      
      // Always use localhost for WebSocket (even on GitHub Pages)
      return 'ws://localhost:8000/ws'
    }
    
    const wsUrl = getWsUrl()
    
    try {
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        if (!mountedRef.current) return
        
        console.log('WebSocket connected')
        setIsConnected(true)
        isConnectingRef.current = false
        onConnectRef.current?.()
        
        // Clear any pending reconnect
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
      }
      
      ws.onmessage = (event) => {
        if (!mountedRef.current) return
        
        try {
          const data = JSON.parse(event.data)
          onMessageRef.current?.(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      ws.onclose = () => {
        if (!mountedRef.current) return
        
        console.log('WebSocket disconnected')
        setIsConnected(false)
        isConnectingRef.current = false
        onDisconnectRef.current?.()
        
        // Clear existing timeout if any
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
        
        // Schedule reconnect if auto-reconnect is enabled and component is still mounted
        if (autoReconnect && mountedRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              console.log('Attempting to reconnect...')
              connect()
            }
          }, reconnectInterval)
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        isConnectingRef.current = false
      }
      
      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      isConnectingRef.current = false
    }
  }, [reconnectInterval, autoReconnect])

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  const disconnect = useCallback(() => {
    mountedRef.current = false
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    
    setIsConnected(false)
  }, [])

  useEffect(() => {
    mountedRef.current = true
    connect()
    
    return () => {
      mountedRef.current = false
      disconnect()
    }
  }, []) // Empty dependency array - only run on mount/unmount

  return {
    isConnected,
    sendMessage,
    disconnect,
    reconnect: connect
  }
}