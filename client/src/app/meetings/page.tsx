"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Plus, Video, Calendar, ChevronRight, ExternalLink } from "lucide-react";

export default function MeetingsListPage() {
  const { data: session } = useSession();
  const [meetings, setMeetings] = useState([]);

  // In a real app, you'd fetch meetings from your API here
  // For now, let's show a "New Meeting" prompt if the list is empty

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Your Meetings</h1>
          <p className="text-muted-foreground">Manage and view summaries for all your sessions.</p>
        </div>
        <Link href="/meetings/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" /> New Meeting
          </Button>
        </Link>
      </div>

      {meetings.length === 0 ? (
        <Card className="border-dashed border-2 py-12">
          <CardContent className="flex flex-col items-center text-center">
            <div className="p-4 bg-primary/5 rounded-full mb-4">
              <Video className="h-8 w-8 text-primary/40" />
            </div>
            <h2 className="text-xl font-semibold mb-2">No meetings yet</h2>
            <p className="text-muted-foreground max-w-xs mb-6">
              Connect your first meeting to start getting AI-powered insights and summaries.
            </p>
            <Link href="/meetings/new">
              <Button variant="outline">Start Your First Meeting</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
            {/* Real meetings will be mapped here later! */}
        </div>
      )}
    </div>
  );
}