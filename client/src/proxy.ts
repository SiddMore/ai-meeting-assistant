/**
 * proxy.ts — Next.js edge proxy for protected route enforcement.
 * Checks for a NextAuth session cookie and redirects unauthenticated users to /auth/login.
 */
import { NextRequest, NextResponse } from "next/server"

export function proxy(request: NextRequest) {
    // NextAuth sets either of these cookies depending on whether the site uses HTTPS
    const sessionToken =
        request.cookies.get("next-auth.session-token")?.value ||
        request.cookies.get("__Secure-next-auth.session-token")?.value

    if (!sessionToken) {
        const loginUrl = new URL("/auth/login", request.url)
        loginUrl.searchParams.set("callbackUrl", request.nextUrl.pathname)
        return NextResponse.redirect(loginUrl)
    }

    return NextResponse.next()
}

export const config = {
    matcher: [
        "/dashboard/:path*",
        "/settings/:path*",
    ],
}
