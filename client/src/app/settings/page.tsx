"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { createApiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
// SAFE ICON IMPORTS - No "Google" or "Microsoft" here
import { 
  Plus, Edit, Trash2, Check, Clock, AlertCircle, Activity, X, 
  ArrowLeftRight, Calendar, Mail, Video, User, Settings, 
  Bell, Shield, CalendarX, MailX, Globe, Layout, MousePointer 
} from "lucide-react";
import { cn } from "@/lib/utils";

// Using Globe for Google and Layout for Microsoft to avoid Lucide import errors
const CALENDAR_PROVIDERS = [
  { id: 'google', name: 'Google Calendar', icon: <Globe className="w-4 h-4" /> },
  { id: 'microsoft', name: 'Microsoft Calendar', icon: <Layout className="w-4 h-4" /> },
  { id: 'none', name: 'None', icon: <CalendarX className="w-4 h-4" /> }
];

const NOTIFICATION_PREFERENCES = [
  { id: 'email', name: 'Email', icon: <Mail className="w-4 h-4" /> },
  { id: 'push', name: 'Push Notification', icon: <Bell className="w-4 h-4" /> },
  { id: 'none', name: 'None', icon: <MailX className="w-4 h-4" /> }
];

const RECORDING_PREFERENCES = [
  { id: 'auto', name: 'Auto-record all meetings', icon: <Video className="w-4 h-4" /> },
  { id: 'prompt', name: 'Ask before recording', icon: <Video className="w-4 h-4" /> },
  { id: 'manual', name: 'Manual only', icon: <MousePointer className="w-4 h-4" /> }
];

export default function SettingsPage() {
  const { data: session, status } = useSession();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editingProfile, setEditingProfile] = useState(false);
  const [calendarProvider, setCalendarProvider] = useState('none');
  const [notificationPref, setNotificationPref] = useState('email');
  const [recordingPref, setRecordingPref] = useState('prompt');
  const [showDisconnectDialog, setShowDisconnectDialog] = useState(false);
  const [showDeleteAccountDialog, setShowDeleteAccountDialog] = useState(false);

  // Initialize API client inside the component or effect to ensure token is ready
  const api = createApiClient((session as any)?.accessToken);

  useEffect(() => {
    if (status === "loading") return;
    if (status === "unauthenticated") {
      setLoading(false);
      return;
    }
    loadUserData();
  }, [status]);

  const loadUserData = async () => {
    try {
      const userData = await api.getUserProfile();
      setUser(userData);
      setCalendarProvider(userData.calendar_provider || 'none');
      setNotificationPref(userData.notification_preferences || 'email');
      setRecordingPref(userData.recording_preferences || 'prompt');
    } catch (error) {
      console.error("Failed to load user data:", error);
      toast.error("Failed to load user data");
    } finally {
      setLoading(false);
    }
  };

  const updateProfile = async (field: string, value: string) => {
    try {
      await api.updateUserProfile({ [field]: value });
      toast.success(`${field} updated successfully`);
      if (field === 'name' || field === 'email') {
        loadUserData();
      }
    } catch (error) {
      console.error(`Failed to update ${field}:`, error);
      toast.error(`Failed to update ${field}`);
    }
  };

  const disconnectCalendar = async () => {
    try {
      await api.disconnectCalendar();
      toast.success("Calendar disconnected successfully");
      setCalendarProvider('none');
      setShowDisconnectDialog(false);
    } catch (error) {
      console.error("Failed to disconnect calendar:", error);
      toast.error("Failed to disconnect calendar");
    }
  };

  const deleteAccount = async () => {
    try {
      await api.deleteAccount();
      toast.success("Account deleted successfully");
      window.location.href = "/auth/login";
    } catch (error) {
      console.error("Failed to delete account:", error);
      toast.error("Failed to delete account");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background p-6 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">User Settings</h1>
            <p className="text-sm text-muted-foreground mt-1">Manage your account preferences and integrations</p>
          </div>
          <Button variant="outline" onClick={() => window.location.reload()} className="gap-2">
            <Settings className="w-4 h-4" /> Refresh
          </Button>
        </div>

        {/* Profile Section */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Profile Information</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setEditingProfile(!editingProfile)}>
                {editingProfile ? "Cancel" : <Edit className="w-4 h-4" />}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Name</Label>
                <Input 
                  disabled={!editingProfile} 
                  value={user?.name || ""} 
                  onChange={(e) => setUser({...user, name: e.target.value})}
                  onBlur={(e) => updateProfile("name", e.target.value)}
                />
              </div>
              <div>
                <Label>Email</Label>
                <Input disabled value={user?.email || ""} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Integrations */}
        <Card className="mb-6">
          <CardHeader><CardTitle>Calendar Integration</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-3 gap-4">
            {CALENDAR_PROVIDERS.map((p) => (
              <Button 
                key={p.id} 
                variant={calendarProvider === p.id ? "default" : "outline"}
                className="h-20 flex-col gap-2"
                onClick={() => setCalendarProvider(p.id)}
              >
                {p.icon} {p.name}
              </Button>
            ))}
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-destructive/50">
          <CardHeader><CardTitle className="text-destructive">Danger Zone</CardTitle></CardHeader>
          <CardContent>
            <Button variant="destructive" onClick={() => setShowDeleteAccountDialog(true)}>
              <Shield className="mr-2 h-4 w-4" /> Delete Account
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Delete Dialog */}
      <Dialog open={showDeleteAccountDialog} onOpenChange={setShowDeleteAccountDialog}>
        <DialogContent>
          <DialogTitle>Are you absolutely sure?</DialogTitle>
          <DialogDescription>This action cannot be undone. All meeting data will be lost.</DialogDescription>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setShowDeleteAccountDialog(false)}>Cancel</Button>
            <Button variant="destructive" onClick={deleteAccount}>Confirm Delete</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}