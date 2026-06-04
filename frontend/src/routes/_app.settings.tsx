import { createFileRoute } from "@tanstack/react-router";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useTheme } from "@/lib/theme";

export const Route = createFileRoute("/_app/settings")({ component: Settings });

function Settings() {
  const { theme, toggle } = useTheme();
  return (
    <>
      <Topbar title="Settings" />
      <main className="space-y-6 p-4 md:p-6 max-w-3xl">
        <Card className="shadow-soft">
          <CardHeader><CardTitle>Account</CardTitle><CardDescription>Update your personal information</CardDescription></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2"><Label>Full name</Label><Input defaultValue="Sarah Chen" /></div>
            <div className="space-y-2"><Label>Email</Label><Input defaultValue="sarah.chen@example.com" /></div>
            <div className="space-y-2"><Label>Country</Label><Input defaultValue="United States" /></div>
            <div className="space-y-2"><Label>Phone</Label><Input defaultValue="+1 (555) 010-2024" /></div>
          </CardContent>
        </Card>
        <Card className="shadow-soft">
          <CardHeader><CardTitle>Preferences</CardTitle><CardDescription>Customize your experience</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: "Dark mode", desc: "Switch theme appearance", checked: theme === "dark", action: toggle },
              { label: "Email notifications", desc: "Job matches and roadmap reminders", checked: true },
              { label: "Weekly progress report", desc: "Every Monday at 9am", checked: true },
              { label: "Public profile", desc: "Let recruiters discover you", checked: false },
            ].map(p => (
              <div key={p.label} className="flex items-center justify-between rounded-lg border p-4">
                <div><p className="font-medium">{p.label}</p><p className="text-xs text-muted-foreground">{p.desc}</p></div>
                <Switch defaultChecked={p.checked} onCheckedChange={p.action} />
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="shadow-soft border-destructive/30">
          <CardHeader><CardTitle className="text-destructive">Danger zone</CardTitle><CardDescription>Permanent account actions</CardDescription></CardHeader>
          <CardContent className="flex gap-2"><Button variant="outline">Export data</Button><Button variant="destructive">Delete account</Button></CardContent>
        </Card>
      </main>
    </>
  );
}
