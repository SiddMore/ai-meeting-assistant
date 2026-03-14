"use client";

import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { UserPlus, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

export default function RegisterPage() {
    const router = useRouter();
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password }),
            });

            if (res.ok) {
                toast.success("Account created successfully! Logging in...");

                // Auto sign-in after successful registration
                const signInRes = await signIn("credentials", {
                    redirect: false,
                    email,
                    password,
                });

                if (signInRes?.error) {
                    toast.error("Account created, but failed to log in automatically.");
                    router.push("/auth/login");
                } else {
                    router.push("/dashboard");
                    router.refresh();
                }
            } else {
                const data = await res.json();
                toast.error(data.detail || "Failed to create account");
            }
        } catch (error) {
            toast.error("Network error. Please try again.");
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
                        <UserPlus className="w-6 h-6 text-primary" />
                    </div>
                    <CardTitle className="text-3xl font-bold tracking-tight">
                        Create an Account
                    </CardTitle>
                    <CardDescription className="text-base mt-2">
                        Sign up to get started with your meeting assistant
                    </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4 px-8">
                    <form onSubmit={handleRegister} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Full Name</Label>
                            <Input
                                id="name"
                                type="text"
                                placeholder="John Doe"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                                className="bg-background/50"
                            />
                        </div>
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
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                minLength={8}
                                className="bg-background/50"
                            />
                        </div>
                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? "Creating account..." : "Sign Up"}
                        </Button>
                    </form>

                </CardContent>

                <CardFooter className="px-8 pb-8 pt-2 flex flex-col items-center gap-4">
                    <p className="text-sm text-center text-muted-foreground">
                        Already have an account?{" "}
                        <Link href="/auth/login" className="font-semibold text-primary hover:underline">
                            Log in
                        </Link>
                    </p>
                </CardFooter>
            </Card>
        </main>
    );
}
