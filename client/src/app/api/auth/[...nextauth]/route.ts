import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import AzureADProvider from "next-auth/providers/azure-ad";
import CredentialsProvider from "next-auth/providers/credentials";

export const authOptions = {
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID || "",
            clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
        }),
        AzureADProvider({
            clientId: process.env.AZURE_AD_CLIENT_ID || "",
            clientSecret: process.env.AZURE_AD_CLIENT_SECRET || "",
            tenantId: process.env.AZURE_AD_TENANT_ID || "common",
        }),
        CredentialsProvider({
            name: "Credentials",
            credentials: {
                email: { label: "Email", type: "email" },
                password: { label: "Password", type: "password" }
            },
            async authorize(credentials) {
                if (!credentials?.email || !credentials?.password) return null;

                try {
                    // FastAPI OAuth2PasswordRequestForm expects form-urlencoded data with 'username' and 'password'
                    const formData = new URLSearchParams();
                    formData.append("username", credentials.email);
                    formData.append("password", credentials.password);

                    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
                        method: "POST",
                        headers: { "Content-Type": "application/x-www-form-urlencoded" },
                        body: formData,
                    });

                    if (res.ok) {
                        const data = await res.json();
                        // Return object that NextAuth uses to populate the JWT
                        return {
                            id: "credentials-id",
                            email: credentials.email,
                            accessToken: data.access_token,
                            provider: "credentials"
                        };
                    }
                    return null; // Login failed
                } catch (error) {
                    console.error("Credentials login failed:", error);
                    return null;
                }
            }
        }),
    ],
    callbacks: {
        async jwt({ token, account, profile, user }: any) {
            // 1. If it's a Credentials login, 'user' will contain the object we returned from authorize()
            if (user && user.provider === "credentials") {
                token.accessToken = user.accessToken;
                token.provider = "credentials";
                return token;
            }

            // 2. Upon successful OAuth login, sync with our FastAPI backend
            if (account && profile) {
                try {
                    // Call our backend /social endpoint
                    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/social`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            email: profile.email || token.email,
                            name: profile.name || token.name,
                            provider: account.provider,
                            provider_id: account.providerAccountId,
                            avatar_url: profile.picture || profile.image || null,
                        }),
                    });

                    if (res.ok) {
                        const data = await res.json();
                        // Store the backend access token in the NextAuth JWT token
                        token.accessToken = data.access_token;
                        token.provider = account.provider;
                    } else {
                        console.error("Failed to sync with backend:", await res.text());
                    }
                } catch (error) {
                    console.error("Error communicating with backend auth:", error);
                }
            }
            return token;
        },
        async session({ session, token }: any) {
            // Expose the access token so the frontend client can use it for API requests
            session.accessToken = token.accessToken;
            session.provider = token.provider;
            return session;
        },
    },
    pages: {
        signIn: "/auth/login",
    },
    session: {
        strategy: "jwt" as const,
    },
    secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
