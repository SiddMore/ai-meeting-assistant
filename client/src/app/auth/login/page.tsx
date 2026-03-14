"use client";

import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { LogIn, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleCredentialsLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await signIn("credentials", {
        redirect: false,
        email,
        password,
      });

      if (res?.error) {
        toast.error("Invalid email or password");
      } else {
        toast.success("Logged in successfully!");
        router.push("/dashboard");
        router.refresh();
      }
    } catch (error) {
      toast.error("Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen relative flex items-center justify-center bg-background overflow-hidden p-4">
      {/* Background Gradients */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute -top-[40%] -left-[20%] w-[70%] h-[70%] rounded-full opacity-20 blur-[100px] bg-primary animate-pulse" />
        <div className="absolute top-[60%] right-[10%] w-[50%] h-[50%] rounded-full opacity-10 blur-[120px] bg-blue-500" />
      </div>

      <Card className="w-full max-w-md border-border/50 bg-card/60 backdrop-blur-xl shadow-2xl relative overflow-hidden">
        {/* Subtle top highlight */}
        <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-primary/50 to-transparent" />

        <CardHeader className="text-center pb-6 pt-10">
          <div className="mx-auto bg-primary/10 p-3 rounded-full w-fit mb-4">
            <Sparkles className="w-6 h-6 text-primary" />
          </div>
          <CardTitle className="text-3xl font-bold tracking-tight">
            Welcome Back
          </CardTitle>
          <CardDescription className="text-base mt-2">
            Sign in to your account
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 px-8">
          <form onSubmit={handleCredentialsLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="m@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-background/50"
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link href="#" className="text-sm font-medium text-primary hover:underline">
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-background/50"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">
                Or continue with
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Button
              variant="outline"
              className="w-full h-11 text-sm font-normal bg-background/50 hover:bg-background/80 hover:shadow-md transition-all duration-300"
              onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
            >
              <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
              Google
            </Button>

            <Button
              variant="outline"
              className="w-full h-11 text-sm font-normal bg-background/50 hover:bg-background/80 hover:shadow-md transition-all duration-300"
              onClick={() => signIn("azure-ad", { callbackUrl: "/dashboard" })}
            >
              <svg className="w-4 h-4 mr-2" viewBox="0 0 21 21">
                <path fill="#f25022" d="M1 1h9v9H1z" />
                <path fill="#7fba00" d="M11 1h9v9h-9z" />
                <path fill="#00a4ef" d="M1 11h9v9H1z" />
                <path fill="#ffb900" d="M11 11h9v9h-9z" />
              </svg>
              Microsoft
            </Button>
          </div>
        </CardContent>

        <CardFooter className="px-8 pb-8 pt-2 flex flex-col items-center gap-4">
          <p className="text-sm text-center text-muted-foreground">
            Don't have an account?{" "}
            <Link href="/auth/register" className="font-semibold text-primary hover:underline">
              Sign up
            </Link>
          </p>
        </CardFooter>
      </Card>
    </main>
  );
}
