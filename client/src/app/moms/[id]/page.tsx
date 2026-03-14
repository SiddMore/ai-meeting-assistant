"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { toast } from "sonner";
import { createApiClient } from "@/lib/api-client";
import {
    Search, Calendar, Clock, User, Filter, ChevronDown, ChevronUp,
    Trash2, ExternalLink, ArrowLeft, ArrowRight, Check, Edit, X, Plus, Printer, Download, FileText
} from "lucide-react";

// (Keep your interfaces here exactly as you have them)

export default function MOMDetailPage() {
    const params = useParams();
    const id = params.id as string;
    const router = useRouter();
    const { data: session } = useSession();
    const api = createApiClient((session as any)?.accessToken);

    const [mom, setMOM] = useState<any>(null); // Simplified for integration
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (id) loadMOM();
    }, [id]);

    const loadMOM = async () => {
        setLoading(true);
        try {
            const response = await api.moms.get(id);
            setMOM(response);
        } catch (err: any) {
            setError("Failed to load MOM");
            toast.error("Could not find this meeting summary");
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="p-20 text-center animate-pulse">Loading Summary...</div>;
    if (!mom) return <div className="p-20 text-center text-red-500">MOM Not Found</div>;

    return (
        <div className="min-h-screen bg-gray-50/50 p-6">
            <div className="max-w-5xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <Button variant="ghost" onClick={() => router.push('/moms')} className="gap-2">
                        <ArrowLeft className="h-4 w-4" /> Back to List
                    </Button>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => window.print()} className="gap-2">
                            <Printer className="h-4 w-4" /> Print
                        </Button>
                        <Button className="gap-2 bg-blue-600 hover:bg-blue-700">
                            <Download className="h-4 w-4" /> Export PDF
                        </Button>
                    </div>
                </div>

                <Card className="mb-8 border-none shadow-sm">
                    <CardHeader className="bg-white border-b border-gray-100 rounded-t-xl">
                        <div className="flex justify-between items-start">
                            <div>
                                <CardTitle className="text-2xl font-bold text-gray-900">
                                    {mom.meeting?.title || "Project Sync"}
                                </CardTitle>
                                <CardDescription className="flex items-center gap-4 mt-2">
                                    <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {new Date(mom.created_at).toLocaleDateString()}</span>
                                    <span className="flex items-center gap-1 font-medium text-blue-600 capitalize">{mom.meeting?.platform?.replace('_', ' ')}</span>
                                </CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="p-8">
                        <div className="space-y-8">
                            <section>
                                <h3 className="text-sm font-semibold uppercase tracking-wider text-blue-600 mb-3 flex items-center gap-2">
                                    <FileText className="h-4 w-4" /> Executive Summary
                                </h3>
                                <p className="text-gray-700 leading-relaxed bg-blue-50/30 p-4 rounded-lg border border-blue-100">
                                    {mom.summary || "No summary available."}
                                </p>
                            </section>

                            <section>
                                <h3 className="text-sm font-semibold uppercase tracking-wider text-green-600 mb-3 flex items-center gap-2">
                                    <Check className="h-4 w-4" /> Key Decisions
                                </h3>
                                <div className="bg-green-50/30 p-4 rounded-lg border border-green-100 text-gray-700">
                                    {mom.key_decisions || "No key decisions recorded."}
                                </div>
                            </section>
                        </div>
                    </CardContent>
                </Card>
                
                {/* Action Items List would go here... */}
            </div>
        </div>
    );
}