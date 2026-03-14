import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default withAuth(
    function middleware(req) {
        return NextResponse.next();
    },
    {
        callbacks: {
            authorized: ({ token }) => !!token,
        },
        pages: {
            signIn: "/auth/login",
        },
    }
);

export const config = {
    // Protect all your main app routes
    matcher: [
        "/dashboard/:path*", 
        "/meetings/:path*", 
        "/tasks/:path*", 
        "/moms/:path*", 
        "/calendar/:path*", 
        "/settings/:path*"
    ],
};
