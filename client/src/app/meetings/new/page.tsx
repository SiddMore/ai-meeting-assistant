"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Video, Plus, ArrowLeft, Globe } from "lucide-react"; // Safe icons
import Link from "next/link";

export default function MeetingsPage() {
  const router = useRouter();
  const { data: session } = useSession();
  
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    // Grabbing the token from the session
    const token = (session as any)?.accessToken;

    if (!token) {
      alert("Security Error: No token found. Please log out and log back in!");
      setLoading(false);
      return;
    }

    try {
      // Backend strictly requires lowercase 'google_meet' or 'zoom'
      const platformName = url.includes("zoom.us") ? "zoom" : "google_meet";

      const response = await fetch('http://localhost:8000/api/v1/meetings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ 
          title: title, 
          platform: platformName,
          meeting_url: url 
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Backend Error:", errorData);
        throw new Error(`Error ${response.status}`);
      }

      // Success! Move to dashboard to see the "Joining" status
      router.push('/dashboard');
      router.refresh(); 
      
    } catch (error) {
      console.error("Connection Error:", error);
      alert("Failed to deploy bot. Check your backend terminal!");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-2xl mt-10">
      <div className="mb-6">
        <Link href="/dashboard" className="text-sm text-muted-foreground flex items-center hover:text-primary">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard
        </Link>
      </div>

      <Card className="border-primary/20 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Video className="h-6 w-6 text-primary" />
            </div>
            <CardTitle className="text-2xl">New AI Assistant</CardTitle>
          </div>
          <CardDescription>
            Enter your meeting details below. Our AI bot will join the call to transcribe and summarize the session.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="title">Meeting Title</Label>
              <Input 
                id="title" 
                placeholder="e.g. Weekly Sync or Project Update" 
                value={title} 
                onChange={(e) => setTitle(e.target.value)} 
                required 
                className="bg-background"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="url">Meeting URL (Google Meet or Zoom)</Label>
              <div className="relative">
                <Input 
                  id="url" 
                  type="url" 
                  placeholder="https://meet.google.com/abc-defg-hij" 
                  value={url} 
                  onChange={(e) => setUrl(e.target.value)} 
                  required 
                  className="pl-10 bg-background"
                />
                <Globe className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              </div>
            </div>
            
            <Button type="submit" className="w-full py-6 text-lg" disabled={loading}>
              {loading ? (
                <span className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  Deploying Bot...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Plus className="h-5 w-5" /> Deploy Bot & Start
                </span>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}