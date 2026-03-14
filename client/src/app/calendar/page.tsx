"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { createApiClient, CalendarEvent } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
    CalendarDays,
    Filter,
    RefreshCcw,
    Circle,
    AlertCircle,
    CheckCircle2,
    Loader2,
} from "lucide-react";

const STATUS_COLORS: Record<CalendarEvent["status"], string> = {
    todo: "bg-amber-500/15 text-amber-400 border-amber-500/40",
    in_progress: "bg-sky-500/15 text-sky-400 border-sky-500/40",
    done: "bg-emerald-500/15 text-emerald-400 border-emerald-500/40",
    cancelled: "bg-slate-500/15 text-slate-400 border-slate-500/40",
};

const PROVIDER_COLORS: Record<CalendarEvent["provider"], string> = {
    google: "text-amber-400",
    microsoft: "text-sky-400",
    none: "text-zinc-400",
};

export default function CalendarPage() {
    const { data: session } = useSession();
    const router = useRouter();
    const api = createApiClient((session as any)?.accessToken);

    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState<CalendarEvent["status"] | "all">("all");
    const [providerFilter, setProviderFilter] = useState<CalendarEvent["provider"] | "all">("all");

    useEffect(() => {
        if (!session) return;

        refreshEvents();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [session]);

    async function refreshEvents() {
        setLoading(true);
        try {
            const now = new Date();
            const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
            const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString();
            const res = await api.calendar.events({ start, end });
            setEvents(res.events);
        } catch (e: any) {
            toast.error(e.message ?? "Failed to load calendar events");
        } finally {
            setLoading(false);
        }
    }

    const filteredEvents = useMemo(() => {
        return events.filter((ev) => {
            if (statusFilter !== "all" && ev.status !== statusFilter) return false;
            if (providerFilter !== "all" && ev.provider !== providerFilter) return false;
            return true;
        });
    }, [events, statusFilter, providerFilter]);

    const eventsByDay = useMemo(() => {
        const map: Record<string, CalendarEvent[]> = {};
        for (const ev of filteredEvents) {
            const d = new Date(ev.start);
            const key = d.toISOString().slice(0, 10);
            if (!map[key]) map[key] = [];
            map[key].push(ev);
        }
        return map;
    }, [filteredEvents]);

    const todayKey = new Date().toISOString().slice(0, 10);

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                        <CalendarDays className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Action Item Calendar</h1>
                        <p className="text-sm text-muted-foreground">
                            See all action items on a timeline, derived from your MOMs.
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        onClick={refreshEvents}
                        disabled={loading}
                    >
                        {loading ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                            <RefreshCcw className="w-3.5 h-3.5" />
                        )}
                        Refresh
                    </Button>
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                    <Filter className="w-3.5 h-3.5" />
                    Filters:
                </span>
                <div className="flex items-center gap-1.5 flex-wrap">
                    <Button
                        size="xs"
                        variant={statusFilter === "all" ? "default" : "outline"}
                        onClick={() => setStatusFilter("all")}
                    >
                        All statuses
                    </Button>
                    {(["todo", "in_progress", "done", "cancelled"] as const).map((s) => (
                        <Button
                            key={s}
                            size="xs"
                            variant={statusFilter === s ? "default" : "outline"}
                            onClick={() => setStatusFilter(s)}
                        >
                            {s.replace("_", " ")}
                        </Button>
                    ))}
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                    <Button
                        size="xs"
                        variant={providerFilter === "all" ? "default" : "outline"}
                        onClick={() => setProviderFilter("all")}
                    >
                        All providers
                    </Button>
                    <Button
                        size="xs"
                        variant={providerFilter === "google" ? "default" : "outline"}
                        onClick={() => setProviderFilter("google")}
                    >
                        <span className={PROVIDER_COLORS.google}>Google</span>
                    </Button>
                    <Button
                        size="xs"
                        variant={providerFilter === "microsoft" ? "default" : "outline"}
                        onClick={() => setProviderFilter("microsoft")}
                    >
                        <span className={PROVIDER_COLORS.microsoft}>Microsoft</span>
                    </Button>
                    <Button
                        size="xs"
                        variant={providerFilter === "none" ? "default" : "outline"}
                        onClick={() => setProviderFilter("none")}
                    >
                        <span className={PROVIDER_COLORS.none}>Local only</span>
                    </Button>
                </div>
            </div>

            <Card className="border-border/40 bg-card/50">
                <CardHeader className="pb-3 flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                        <CalendarDays className="w-4 h-4 text-primary" />
                        This month
                    </CardTitle>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1">
                            <Circle className="w-2.5 h-2.5 text-amber-400" /> Todo
                        </span>
                        <span className="inline-flex items-center gap-1">
                            <Circle className="w-2.5 h-2.5 text-sky-400" /> In progress
                        </span>
                        <span className="inline-flex items-center gap-1">
                            <Circle className="w-2.5 h-2.5 text-emerald-400" /> Done
                        </span>
                    </div>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="flex items-center justify-center h-40 text-sm text-muted-foreground gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Loading events...
                        </div>
                    ) : filteredEvents.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-40 text-center gap-2 text-muted-foreground">
                            <AlertCircle className="w-5 h-5 opacity-40" />
                            <p className="text-sm">No action items in this range.</p>
                            <p className="text-xs opacity-60">Once MOMs have action items with deadlines, they’ll appear here.</p>
                        </div>
                    ) : (
                        <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1 scrollbar-thin">
                            {Object.entries(eventsByDay)
                                .sort(([a], [b]) => (a < b ? -1 : 1))
                                .map(([day, dayEvents]) => {
                                    const isToday = day === todayKey;
                                    const dateObj = new Date(day);
                                    const label = dateObj.toLocaleDateString("en-IN", {
                                        weekday: "short",
                                        day: "numeric",
                                        month: "short",
                                    });
                                    return (
                                        <div key={day} className="space-y-1.5">
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                                    {label}
                                                </span>
                                                {isToday && (
                                                    <Badge
                                                        variant="outline"
                                                        className="h-5 px-1.5 text-[10px] border-emerald-500/40 text-emerald-400"
                                                    >
                                                        Today
                                                    </Badge>
                                                )}
                                                <span className="text-[11px] text-muted-foreground/70">
                                                    · {dayEvents.length} item{dayEvents.length !== 1 ? "s" : ""}
                                                </span>
                                            </div>
                                            <div className="grid gap-1.5">
                                                {dayEvents.map((ev) => {
                                                    const start = new Date(ev.start).toLocaleTimeString("en-IN", {
                                                        hour: "2-digit",
                                                        minute: "2-digit",
                                                    });
                                                    const providerLabel =
                                                        ev.provider === "google"
                                                            ? "Google"
                                                            : ev.provider === "microsoft"
                                                            ? "Microsoft"
                                                            : "Local";
                                                    return (
                                                        <button
                                                            key={ev.id}
                                                            className="w-full text-left px-3 py-2 rounded-lg border border-border/50 bg-background/40 hover:bg-background/80 flex items-start justify-between gap-3 transition-colors"
                                                            onClick={() => {
                                                                if (ev.mom_id) {
                                                                    router.push(`/moms/${ev.mom_id}`);
                                                                }
                                                            }}
                                                        >
                                                            <div className="flex items-start gap-2">
                                                                <span className="mt-1 text-[10px] text-muted-foreground">
                                                                    {start}
                                                                </span>
                                                                <div>
                                                                    <div className="flex items-center gap-2">
                                                                        <p className="text-sm font-medium">
                                                                            {ev.title}
                                                                        </p>
                                                                        <Badge
                                                                            variant="outline"
                                                                            className={`h-5 px-1.5 text-[10px] border ${STATUS_COLORS[ev.status]}`}
                                                                        >
                                                                            {ev.status.replace("_", " ")}
                                                                        </Badge>
                                                                    </div>
                                                                    <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground">
                                                                        <span
                                                                            className={PROVIDER_COLORS[ev.provider]}
                                                                        >
                                                                            {providerLabel}
                                                                        </span>
                                                                        <span>•</span>
                                                                        <span className="capitalize">
                                                                            {ev.priority} priority
                                                                        </span>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            {ev.status === "done" && (
                                                                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                                                            )}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    );
                                })}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

