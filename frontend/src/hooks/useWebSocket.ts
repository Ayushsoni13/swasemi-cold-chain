import { useEffect, useRef, useState, useCallback } from 'react';
import type { WSTelemetryEvent } from '../types';

export type ConnectionState = 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING';

export function useWebSocket(token: string | null, onMessage: (event: WSTelemetryEvent) => void) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('DISCONNECTED');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef<number>(2000); // Initial backoff 2 seconds
  const isUnmountedRef = useRef<boolean>(false);

  const connect = useCallback(() => {
    if (!token || isUnmountedRef.current) return;

    const baseUrl = import.meta.env.VITE_BACKEND_URL || window.location.origin;
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const cleanHost = baseUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${cleanHost}/ws?token=${token}`;

    setConnectionState((prev) => (prev === 'DISCONNECTED' ? 'RECONNECTING' : prev));

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmountedRef.current) {
          ws.close();
          return;
        }
        setConnectionState('CONNECTED');
        reconnectDelayRef.current = 2000;
      };

      ws.onmessage = (event) => {
        try {
          const data: WSTelemetryEvent = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {
          console.error('Error parsing WS message:', e);
        }
      };

      ws.onerror = (error) => {
        console.warn('WebSocket error encountered:', error);
      };

      ws.onclose = () => {
        if (isUnmountedRef.current) return;
        setConnectionState('RECONNECTING');

        const nextDelay = Math.min(reconnectDelayRef.current * 1.5, 10000);
        reconnectDelayRef.current = nextDelay;

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, nextDelay);
      };
    } catch (err) {
      console.error('WebSocket connection failed:', err);
      setConnectionState('DISCONNECTED');
    }
  }, [token, onMessage]);

  useEffect(() => {
    isUnmountedRef.current = false;
    if (token) {
      connect();
    }

    return () => {
      isUnmountedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      setConnectionState('DISCONNECTED');
    };
  }, [token, connect]);

  return { connectionState };
}
