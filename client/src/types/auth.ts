/**
 * TypeScript type augmentation for next-auth
 * Extends Session and JWT to include user.id
 */
import type { DefaultSession, DefaultUser } from "next-auth"
import type { DefaultJWT } from "next-auth/jwt"

declare module "next-auth" {
    interface Session {
        user: {
            id: string
        } & DefaultSession["user"]
    }
    interface User extends DefaultUser {
        id: string
    }
}

declare module "next-auth/jwt" {
    interface JWT extends DefaultJWT {
        id?: string
    }
}

// ── App User type (from backend) ──────────────────────────────────────────────
export interface AppUser {
    id: string
    email: string
    name: string
    avatar_url: string | null
    oauth_provider: string | null
    is_active: boolean
    is_verified: boolean
    created_at: string
}
