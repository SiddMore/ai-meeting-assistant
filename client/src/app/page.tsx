import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center gap-6 p-8">
      <div className="text-center space-y-3 max-w-2xl">
        <h1 className="text-5xl font-bold tracking-tight text-foreground">
          AI Meeting Assistant
        </h1>
        <p className="text-xl text-muted-foreground">
          Join meetings, capture transcripts in Hindi/Marathi & English,
          generate MOMs, and sync tasks to your calendar — automatically.
        </p>
      </div>
      <div className="flex gap-4">
        <Button asChild size="lg">
          <Link href="/auth/login">Get Started</Link>
        </Button>
        <Button asChild variant="outline" size="lg">
          <Link href="/dashboard">Dashboard</Link>
        </Button>
      </div>
    </main>
  );
}
