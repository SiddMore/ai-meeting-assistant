/**
 * socket.ts — Socket.IO client singleton.
 * Import `socket` wherever you need real-time communication.
 * The connection is lazy — it only opens when first used.
 */
import { io, Socket } from "socket.io-client";

const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL ?? "http://127.0.0.1:8000";

let socket: Socket | null = null;

export function getSocket(token?: string): Socket {
    if (!socket) {
        socket = io(SOCKET_URL, {
            transports: ["websocket", "polling"],
            autoConnect: false,
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 500,
            reconnectionDelayMax: 5000,
            timeout: 10000,
            auth: token ? { token } : undefined,
        });

        // Explicit error handling for dropped connections / network flakiness.
        socket.on("connect_error", (err) => {
            console.error("[socket] connect_error:", err?.message ?? err);
        });
        socket.on("disconnect", (reason) => {
            console.warn("[socket] disconnected:", reason);
        });
        socket.on("reconnect_attempt", (attempt) => {
            console.log("[socket] reconnect_attempt:", attempt);
        });
    }
    return socket;
}

/** Connect and join a meeting room to receive live events. */
export function joinMeetingRoom(meetingId: string, token?: string): Socket {
    const s = getSocket(token);
    if (!s.connected) s.connect();
    s.emit("join_meeting", { meeting_id: meetingId, token }, (ack: any) => {
        if (!ack?.ok) console.warn("[socket] join_meeting failed:", ack);
    });
    return s;
}

/** Leave a meeting room and optionally disconnect. */
export function leaveMeetingRoom(meetingId: string) {
    const s = getSocket();
    s.emit("leave_meeting", { meeting_id: meetingId }, (ack: any) => {
        if (ack && ack.ok === false) console.warn("[socket] leave_meeting failed:", ack);
    });
}

export default getSocket;
