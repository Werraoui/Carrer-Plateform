import { Moon, Sun, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useTheme } from "@/lib/theme";
import { useAuth } from "@/lib/auth-context";

export function Topbar({ title }: { title: string }) {
  const { theme, toggle } = useTheme();
  const { user } = useAuth();

  const initials = user?.name
    ? user.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : "?";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-md md:px-6">
      <SidebarTrigger />
      <h1 className="font-display text-lg font-semibold tracking-tight md:text-xl">{title}</h1>
      <div className="ml-auto flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
          {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </Button>
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </Button>
        <div className="ml-1 flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary text-sm font-semibold text-primary-foreground">
          {initials}
        </div>
      </div>
    </header>
  );
}
