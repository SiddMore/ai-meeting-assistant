"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Calendar, ArrowRight, Search } from "lucide-react";
import { createApiClient } from "@/lib/api-client";

export default function MOMsListPage() {
  const { data: session } = useSession();
  const api = createApiClient((session as any)?.accessToken);
  const [moms, setMoms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMoms = async () => {
      try {
        // This assumes your backend has a list endpoint for MOMs
        const data = await api.moms.list(); 
        setMoms(data);
      } catch (error) {
        console.error("Failed to fetch MOMs:", error);
      } finally {
        setLoading(false);
      }
    };
    if (session) fetchMoms();
  }, [session]);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Meeting Minutes</h1>
      <p className="text-muted-foreground mb-8">Review summaries and action items from your past meetings.</p>

      {loading ? (
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => <div key={i} className="h-24 bg-muted rounded-lg" />)}
        </div>
      ) : moms.length === 0 ? (
        <Card className="text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground/30 mb-4" />
          <p>No meeting minutes found. Complete a meeting to see it here!</p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {moms.map((mom) => (
            <Card key={mom.id} className="hover:border-primary/50 transition-colors">
              <CardContent className="flex items-center justify-between p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-blue-50 rounded-full">
                    <FileText className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">{mom.meeting?.title || "Untitled Meeting"}</h3>
                    <p className="text-sm text-muted-foreground flex items-center gap-2">
                      <Calendar className="h-3 w-3" /> {new Date(mom.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <Link href={`/moms/${mom.id}`}>
                  <Button variant="ghost" className="gap-2">
                    View Minutes <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}