"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { createApiClient, MeetingOut, TranscriptChunk } from "@/lib/api-client";
// Path check: Ensure this points to your new hooks folder
import { useMeetingSocket } from "@/hooks/useMeetingSocket";
import {
    ArrowLeft, Radio, Clock, CheckCircle, AlertCircle, Activity,
    Loader2, MessageSquare, Search, RefreshCw, ArrowDown
} from "lucide-react";

import { useDebouncedCallback } from "use-debounce";

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
    scheduled: { label: "Scheduled", color: "text-blue-400", bg: "bg-blue-400/10", icon: <Clock className="w-3.5 h-3.5" /> },
    bot_joining: { label: "Joining...", color: "text-yellow-400", bg: "bg-yellow-400/10", icon: <Loader2 className="w-3.5 h-3.5 animate-spin" /> },
    in_progress: { label: "Live", color: "text-green-400", bg: "bg-green-400/10", icon: <Radio className="w-3.5 h-3.5 animate-pulse" /> },
    processing: { label: "Processing", color: "text-purple-400", bg: "bg-purple-400/10", icon: <Activity className="w-3.5 h-3.5" /> },
    completed: { label: "Completed", color: "text-emerald-400", bg: "bg-emerald-400/10", icon: <CheckCircle className="w-3.5 h-3.5" /> },
    failed: { label: "Failed", color: "text-red-400", bg: "bg-red-400/10", icon: <AlertCircle className="w-3.5 h-3.5" /> },
};

export default function MeetingPage() {
    const params = useParams();
    const id = params.id as string;
    const router = useRouter();
    const { data: session } = useSession();
    const api = createApiClient((session as any)?.accessToken);

    // State management
    const [meeting, setMeeting] = useState<MeetingOut | null>(null);
    const [chunks, setChunks] = useState<TranscriptChunk[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [autoScroll, setAutoScroll] = useState(true);

    const scrollRef = useRef<HTMLDivElement>(null);
    const bottomRef = useRef<HTMLDivElement>(null);

    // ── PHASE 1: Real-time Sync Hook ──────────────────────────────────
    const { status: liveStatus, isConnected, socket } = useMeetingSocket(id, (session as any)?.accessToken) as any;

    // Effect for initial data loading
    useEffect(() => {
        if (!id || !session) return;

        const loadMeetingData = async () => {
            try {
                const [m, t] = await Promise.all([
                    api.meetings.get(id),
                    api.meetings.getTranscript(id)
                ]);
                setMeeting(m);
                setChunks(t);
                setLoading(false);
            } catch (err: any) {
                toast.error("Failed to load meeting data");
                setLoading(false);
            }
        };
        loadMeetingData();
    }, [id, session]);

    // Listen for live transcript chunks via the hook's socket
    useEffect(() => {
        if (!socket) return;

        socket.on("transcript.data", (data: { chunk: TranscriptChunk }) => {
            setChunks((prev) => [...prev, data.chunk]);
            if (autoScroll) scrollToBottom();
        });

        return () => { socket.off("transcript.data"); };
    }, [socket, autoScroll]);

    const scrollToBottom = () => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const currentStatus = liveStatus || meeting?.status || "scheduled";
    const config = STATUS_CONFIG[currentStatus] || STATUS_CONFIG.scheduled;

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
            <div className="max-w-5xl mx-auto space-y-6">
                
                {/* Header */}
                <div className="flex items-center justify-between">
                    <Button variant="ghost" onClick={() => router.back()} className="text-slate-400 hover:text-white">
                        <ArrowLeft className="w-4 h-4 mr-2" /> Back
                    </Button>
                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${config.bg} ${config.color} border border-white/5`}>
                        {config.icon}
                        <span className="text-sm font-medium">{config.label}</span>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left: Meeting Details */}
                    <div className="lg:col-span-1 space-y-6">
                        <Card className="bg-slate-900 border-slate-800">
                            <CardHeader>
                                <CardTitle className="text-xl text-white">{meeting?.title}</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4 text-sm text-slate-400">
                                <div className="flex justify-between">
                                    <span>Connection</span>
                                    <span className={isConnected ? "text-green-400" : "text-red-400"}>
                                        {isConnected ? "Active" : "Disconnected"}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Started</span>
                                    <span>{meeting?.created_at ? new Date(meeting.created_at).toLocaleTimeString() : "-"}</span>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Right: Live Transcript Area */}
                    <div className="lg:col-span-2 flex flex-col h-[70vh] bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50 backdrop-blur">
                            <h2 className="font-semibold flex items-center gap-2">
                                <Activity className="w-4 h-4 text-blue-500" /> Live Transcript
                            </h2>
                            <Button size="sm" variant="outline" onClick={() => setAutoScroll(!autoScroll)} 
                                className={autoScroll ? "border-blue-500 text-blue-500" : ""}>
                                Auto-scroll {autoScroll ? "On" : "Off"}
                            </Button>
                        </div>

                        {/* Scrollable Area */}
                        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                            {chunks.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
                                    <MessageSquare className="w-8 h-8 opacity-20" />
                                    <p>Waiting for transcript...</p>
                                </div>
                            ) : (
                                chunks.map((chunk, i) => (
                                    <div key={i} className="group animate-in fade-in slide-in-from-bottom-2">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
                                                {chunk.speaker || "Speaker"}
                                            </span>
                                            <span className="text-[10px] text-slate-600">
                                                {new Date(chunk.created_at).toLocaleTimeString()}
                                            </span>
                                        </div>
                                        <p className="text-slate-300 leading-relaxed bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                                            {chunk.text}
                                        </p>
                                    </div>
                                ))
                            )}
                            <div ref={bottomRef} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}