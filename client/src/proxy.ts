/**
 * proxy.ts — Next.js 16 combined gateway.
 * Merges your previous NextAuth logic with the new Proxy naming convention.
 */
import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default withAuth(
    function proxy(req) {
        // This runs if the user is authorized.
        return NextResponse.next();
    },
    {
        callbacks: {
            // This is the logic you had before: check if token exists
            authorized: ({ token }) => !!token,
        },
        pages: {
            // Your custom login page
            signIn: "/auth/login",
        },
    }
);

export const config = {
    // We've put all your important routes back on the "protected" list
    matcher: [
        "/dashboard/:path*", 
        "/meetings/:path*", 
        "/tasks/:path*", 
        "/moms/:path*", 
        "/calendar/:path*", 
        "/settings/:path*"
    ],
};