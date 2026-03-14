// Dashboard layout — wraps all dashboard sub-pages with sidebar and navbar
import Link from "next/link";

const NAV_ITEMS = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Meetings", href: "/meetings" }, // Removed /dashboard
    { label: "Tasks", href: "/tasks" },       // Removed /dashboard
    { label: "MOMs", href: "/moms" },         // Removed /dashboard
    { label: "Calendar", href: "/calendar" }, // Removed /dashboard
    { label: "Settings", href: "/settings" }, // Removed /dashboard
];

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen flex">
            {/* Sidebar */}
            <aside className="w-64 bg-card border-r border-border p-4 hidden md:block">
                <nav className="space-y-1">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">
                        Navigation
                    </p>
                    {NAV_ITEMS.map((item) => (
                        <Link
                            key={item.label}
                            href={item.href}
                            className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                        >
                            {item.label}
                        </Link>
                    ))}
                </nav>
            </aside>
            <main className="flex-1 p-6">{children}</main>
        </div>
    );
}
