import { createFileRoute } from "@tanstack/react-router";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { extractedSkills } from "@/lib/mock-data";

export const Route = createFileRoute("/_app/progress")({ component: SkillProgress });

const tracked = extractedSkills.map(s => ({ ...s, target: Math.min(100, s.level + 15) }));

function SkillProgress() {
  return (
    <>
      <Topbar title="Skill Progress" />
      <main className="space-y-6 p-4 md:p-6">
        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { label: "Skills tracked", value: tracked.length, sub: "Across 5 categories" },
            { label: "Avg. completion", value: "74%", sub: "+8% this month" },
            { label: "Achievements", value: 12, sub: "3 unlocked recently" },
          ].map(s => (
            <Card key={s.label} className="shadow-soft"><CardContent className="p-5"><p className="text-xs uppercase tracking-wider text-muted-foreground">{s.label}</p><p className="mt-2 font-display text-3xl font-bold">{s.value}</p><p className="text-xs text-muted-foreground">{s.sub}</p></CardContent></Card>
          ))}
        </div>

        <Card className="shadow-soft">
          <CardHeader><CardTitle>Current vs Target Level</CardTitle><CardDescription>How close are you on each skill?</CardDescription></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tracked} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis type="number" domain={[0, 100]} stroke="var(--color-muted-foreground)" fontSize={12} />
                <YAxis type="category" dataKey="name" stroke="var(--color-muted-foreground)" fontSize={12} width={110} />
                <Tooltip contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 12 }} />
                <Bar dataKey="level" name="Current" fill="var(--color-primary)" radius={[0,6,6,0]} />
                <Bar dataKey="target" name="Target" fill="var(--color-secondary)" radius={[0,6,6,0]} fillOpacity={0.45} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <div className="grid gap-4 md:grid-cols-2">
          {tracked.map(s => (
            <Card key={s.name} className="shadow-soft">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div><p className="font-semibold">{s.name}</p><Badge variant="outline" className="mt-1 text-xs">{s.category}</Badge></div>
                  <div className="text-right"><div className="font-display text-2xl font-bold text-primary">{s.level}%</div><div className="text-xs text-muted-foreground">target {s.target}%</div></div>
                </div>
                <Progress value={s.level} className="mt-4 h-2" />
                <div className="mt-2 flex justify-between text-xs text-muted-foreground"><span>Current</span><span>{Math.round((s.level/s.target)*100)}% of goal</span></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </>
  );
}
