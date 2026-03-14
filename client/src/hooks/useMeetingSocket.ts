import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export const useMeetingSocket = (meetingId: string | undefined, token: string | null) => {
  const [status, setStatus] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!meetingId || !token) return;

    const socketInstance = io('http://localhost:8000', {
      auth: { token },
      transports: ['websocket'],
    });

    socketInstance.on('connect', () => {
      console.log('🔌 Socket connected to backend!');
      setIsConnected(true);
      socketInstance.emit('join_meeting', { meeting_id: meetingId, token });
    });

    socketInstance.on('meeting.completed', () => {
      setStatus('completed');
    });

    socketInstance.on('meeting.snapshot', (data) => {
      if (data?.meeting?.status) setStatus(data.meeting.status);
    });

    return () => {
      socketInstance.disconnect();
    };
  }, [meetingId, token]);

  return { status, isConnected };
};