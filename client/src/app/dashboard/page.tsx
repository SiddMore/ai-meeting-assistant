"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Card, CardContent, CardHeader, CardTitle, CardDescription,
} from "@/components/ui/card";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { createApiClient, MeetingListItem } from "@/lib/api-client";
import {
    Video, Plus, Loader2, ExternalLink, Trash2,
    Clock, CheckCircle, AlertCircle, Activity, Radio,
} from "lucide-react";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    scheduled: { label: "Scheduled", color: "text-blue-400", icon: <Clock className="w-3 h-3" /> },
    bot_joining: { label: "Joining", color: "text-yellow-400", icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    in_progress: { label: "Recording", color: "text-green-400", icon: <Radio className="w-3 h-3 animate-pulse" /> },
    processing: { label: "Processing", color: "text-purple-400", icon: <Activity className="w-3 h-3" /> },
    completed: { label: "Completed", color: "text-emerald-400", icon: <CheckCircle className="w-3 h-3" /> },
    failed: { label: "Failed", color: "text-red-400", icon: <AlertCircle className="w-3 h-3" /> },
};

const PLATFORM_LABELS: Record<string, string> = {
    google_meet: "Google Meet",
    zoom: "Zoom",
    teams: "Microsoft Teams",
    other: "Other",
};

export default function DashboardPage() {
    const router = useRouter();
    const { data: session, status } = useSession();
    
    // FIX INTEGRATED: Re-create the API client only when the session actually updates
    const api = useMemo(() => {
        return createApiClient((session as any)?.accessToken);
    }, [session]);

    const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
    const [loadingMeetings, setLoadingMeetings] = useState(true);

    useEffect(() => {
        if (status === "loading") return;
        if (status === "unauthenticated") {
            setLoadingMeetings(false);
            return;
        }

        // Wait until session and the token are fully ready
        if (!session || !(session as any).accessToken) return;

        api.meetings.list()
            .then(setMeetings)
            .catch((e) => toast.error(e.message || "Failed to load meetings"))
            .finally(() => setLoadingMeetings(false));
    }, [session, status, api]); // Updated dependency array



    async function handleDelete(id: string, e: React.MouseEvent) {
        e.stopPropagation();
        try {
            await api.meetings.delete(id);
            setMeetings((prev) => prev.filter((m) => m.id !== id));
            toast.success("Meeting removed");
        } catch {
            toast.error("Failed to delete meeting");
        }
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Meetings</h1>
                    <p className="text-muted-foreground mt-1">Deploy a bot to any meeting URL and get live transcripts.</p>
                </div>
                <Link href="/meetings/new">
                    <Button className="gap-2">
                        <Plus className="w-4 h-4" />
                        New Meeting
                    </Button>
                </Link>
            </div>



            {/* Meeting List */}
            {loadingMeetings ? (
                <div className="flex items-center justify-center h-40">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
            ) : meetings.length === 0 ? (
                <Card className="border-dashed border-border/50 bg-card/40">
                    <CardContent className="flex flex-col items-center justify-center py-16 gap-4 text-center">
                        <Video className="w-12 h-12 text-muted-foreground/40" />
                        <div>
                            <p className="font-semibold text-muted-foreground">No meetings yet</p>
                            <p className="text-sm text-muted-foreground/60 mt-1">
                                Click &quot;New Meeting&quot; to deploy a bot to your first meeting.
                            </p>
                        </div>
                        <Link href="/meetings/new">
                            <Button variant="outline" className="gap-2">
                                <Plus className="w-4 h-4" /> New Meeting
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-3">
                    {meetings.map((meeting) => {
                        const status = STATUS_CONFIG[meeting.status] ?? STATUS_CONFIG.scheduled;
                        return (
                            <Link key={meeting.id} href={`/meetings/${meeting.id}`}>
                                <Card className="border-border/40 bg-card/50 hover:bg-card/80 hover:border-primary/30 transition-all cursor-pointer group">
                                    <CardContent className="flex items-center justify-between p-4">
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                                                <Video className="w-5 h-5 text-primary" />
                                            </div>
                                            <div>
                                                <p className="font-semibold group-hover:text-primary transition-colors">
                                                    {meeting.title || "Untitled Meeting"}
                                                </p>
                                                <p className="text-xs text-muted-foreground mt-0.5">
                                                    {PLATFORM_LABELS[meeting.platform] ?? meeting.platform} ·{" "}
                                                    {new Date(meeting.created_at).toLocaleDateString("en-IN", {
                                                        day: "numeric", month: "short", year: "numeric",
                                                    })}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className={`flex items-center gap-1.5 text-xs font-medium ${status.color}`}>
                                                {status.icon}
                                                {status.label}
                                            </span>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="w-7 h-7 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-all"
                                                onClick={(e) => handleDelete(meeting.id, e)}
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </Button>
                                            <ExternalLink className="w-4 h-4 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
                                        </div>
                                    </CardContent>
                                </Card>
                            </Link>
                        );
                    })}
                </div>
            )}
        </div>
    );
}