import { useEffect, useRef, useState, useCallback } from 'react'

interface UseWebSocketOptions {
  onMessage?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectInterval?: number
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    reconnectInterval = 2000
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      onConnect?.()
      
      // Clear any pending reconnect
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      onDisconnect?.()
      
      // Schedule reconnect
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('Attempting to reconnect...')
        connect()
      }, reconnectInterval)
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    wsRef.current = ws
  }, [onMessage, onConnect, onDisconnect, reconnectInterval])

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    isConnected,
    sendMessage,
    disconnect,
    reconnect: connect
  }
}