import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Circle, BookOpen, Code, FolderGit2, Lightbulb, Loader2, Map } from "lucide-react";
import { toast } from "sonner";
import { generateRoadmap, listRoadmaps, updateStepProgress, type RoadmapOut, type RoadmapStep } from "@/lib/api/roadmap";
import { getGapHistory, type GapResult } from "@/lib/api/gap";
import { formatApiError } from "@/lib/api/client";

export const Route = createFileRoute("/_app/roadmap")({ component: Roadmap });

const typeIcon: Record<string, React.ReactNode> = {
  course: <BookOpen className="h-4 w-4" />,
  project: <FolderGit2 className="h-4 w-4" />,
  practice: <Code className="h-4 w-4" />,
};

const typeBadge: Record<string, string> = {
  course: "bg-blue-500/10 text-blue-600",
  project: "bg-purple-500/10 text-purple-600",
  practice: "bg-orange-500/10 text-orange-600",
};

function weekColor(w: number) {
  const colors = [
    "bg-rose-500","bg-orange-500","bg-amber-500","bg-yellow-500",
    "bg-lime-500","bg-green-500","bg-teal-500","bg-cyan-500",
    "bg-blue-500","bg-indigo-500","bg-violet-500","bg-purple-500",
  ];
  return colors[(w - 1) % colors.length];
}

function StepCard({ step, onToggle }: { step: RoadmapStep & { status?: string }; onToggle: (id: number, status: string) => void }) {
  const done = step.status === "completed";
  return (
    <div className={`group relative rounded-xl border bg-card p-4 shadow-sm transition-all hover:shadow-md ${done ? "opacity-70" : ""}`}>
      <div className="flex items-start gap-3">
        <button
          onClick={() => onToggle(step.id, done ? "not_started" : "completed")}
          className="mt-0.5 shrink-0 text-muted-foreground hover:text-primary transition-colors"
        >
          {done ? <CheckCircle2 className="h-5 w-5 text-success" /> : <Circle className="h-5 w-5" />}
        </button>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-sm">{step.title}</span>
            {step.type && (
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${typeBadge[step.type] ?? "bg-muted text-muted-foreground"}`}>
                {typeIcon[step.type]}{step.type}
              </span>
            )}
            {step.skill_name && <Badge variant="outline" className="text-xs">{step.skill_name}</Badge>}
          </div>
          {step.description && <p className="mt-1.5 text-sm text-muted-foreground">{step.description}</p>}
          {step.tip && (
            <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-primary/5 px-3 py-2 text-xs text-primary">
              <Lightbulb className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>{step.tip}</span>
            </div>
          )}
          {step.resource_link && (
            <a href={step.resource_link} target="_blank" rel="noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline">
              Voir la ressource →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function Roadmap() {
  const [gapHistory, setGapHistory] = useState<GapResult[]>([]);
  const [existingRoadmaps, setExistingRoadmaps] = useState<RoadmapOut[]>([]);
  const [selectedGap, setSelectedGap] = useState<string>("");
  const [selectedWeeks, setSelectedWeeks] = useState<string>("8");
  const [generating, setGenerating] = useState(false);
  const [roadmap, setRoadmap] = useState<RoadmapOut | null>(null);
  const [stepStatus, setStepStatus] = useState<Record<number, string>>({});

  useEffect(() => {
    getGapHistory().then(setGapHistory).catch(() => {});
    listRoadmaps().then((list) => {
      setExistingRoadmaps(list);
      if (list.length > 0) setRoadmap(list[0]);
    }).catch(() => {});
  }, []);

  async function handleGenerate() {
    if (!selectedGap) return toast.error("Sélectionne un gap analysé.");
    setGenerating(true);
    try {
      const res = await generateRoadmap(Number(selectedGap), Number(selectedWeeks), true, true);
      setRoadmap(res);
      setStepStatus({});
      toast.success("Roadmap générée !");
    } catch (err: any) {
      toast.error(formatApiError(err, "Erreur lors de la génération."));
    } finally {
      setGenerating(false);
    }
  }

  async function handleToggle(stepId: number, status: string) {
    setStepStatus((prev) => ({ ...prev, [stepId]: status }));
    try {
      await updateStepProgress(stepId, status as any);
    } catch {
      setStepStatus((prev) => ({ ...prev, [stepId]: status === "completed" ? "not_started" : "completed" }));
    }
  }

  const allSteps = roadmap?.steps ?? [];
  const completedCount = allSteps.filter((s) => (stepStatus[s.id] ?? (s as any).status) === "completed").length;
  const progressPct = allSteps.length > 0 ? Math.round((completedCount / allSteps.length) * 100) : 0;

  // Group steps by week
  const weeks = allSteps.reduce<Record<number, (RoadmapStep & { status?: string })[]>>((acc, s) => {
    const w = s.week_number;
    if (!acc[w]) acc[w] = [];
    acc[w].push({ ...s, status: stepStatus[s.id] ?? (s as any).status ?? "not_started" });
    return acc;
  }, {});

  return (
    <>
      <Topbar title="Roadmap" />
      <main className="mx-auto max-w-[1200px] space-y-6 p-4 md:p-8">

        {/* Generator card */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Générer une roadmap</CardTitle>
            <CardDescription>Basée sur ton dernier gap analysé</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[180px] space-y-1.5">
              <label className="text-sm font-medium">Gap analysé</label>
              <Select value={selectedGap} onValueChange={setSelectedGap}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner..." />
                </SelectTrigger>
                <SelectContent>
                  {gapHistory.length === 0 && (
                    <SelectItem value="none" disabled>Aucun gap — analyse d'abord</SelectItem>
                  )}
                  {gapHistory.map((g) => (
                    <SelectItem key={g.career_gap_id} value={String(g.career_gap_id)}>
                      Gap #{g.career_gap_id} — Score {Math.round(g.employability_score)}%
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[140px] space-y-1.5">
              <label className="text-sm font-medium">Durée (semaines)</label>
              <Select value={selectedWeeks} onValueChange={setSelectedWeeks}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[4, 6, 8, 10, 12].map((n) => (
                    <SelectItem key={n} value={String(n)}>{n} semaines</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleGenerate} disabled={generating}>
              {generating
                ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Génération...</>
                : "Générer ma roadmap"}
            </Button>
          </CardContent>
        </Card>

        {/* Roadmap display */}
        {roadmap && (
          <>
            {/* Header */}
            <div className="rounded-2xl border bg-gradient-to-br from-primary/5 to-secondary/5 p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="font-display text-xl font-bold">{roadmap.job_name}</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    {roadmap.duration_weeks} semaines · {allSteps.length} étapes · moteur {roadmap.engine}
                  </p>
                  {roadmap.intro && <p className="mt-3 text-sm leading-relaxed max-w-2xl">{roadmap.intro}</p>}
                  {roadmap.market_insight && (
                    <div className="mt-3 flex items-start gap-2 rounded-lg bg-primary/10 px-3 py-2 text-sm text-primary max-w-xl">
                      <Lightbulb className="h-4 w-4 mt-0.5 shrink-0" />
                      <span>{roadmap.market_insight}</span>
                    </div>
                  )}
                </div>
                <div className="rounded-xl border bg-card px-5 py-3 shadow-sm">
                  <div className="text-center">
                    <div className="font-display text-3xl font-bold text-primary">{progressPct}%</div>
                    <div className="text-xs text-muted-foreground mt-0.5">complété</div>
                  </div>
                  <Progress value={progressPct} className="mt-2 h-1.5 w-28" />
                  <div className="mt-1 text-center text-xs text-muted-foreground">{completedCount}/{allSteps.length} étapes</div>
                </div>
              </div>
            </div>

            {/* Weeks */}
            <div className="space-y-8">
              {Object.entries(weeks)
                .sort(([a], [b]) => Number(a) - Number(b))
                .map(([week, steps]) => {
                  const doneInWeek = steps.filter((s) => s.status === "completed").length;
                  return (
                    <div key={week}>
                      <div className="mb-3 flex items-center gap-3">
                        <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white ${weekColor(Number(week))}`}>
                          S{week}
                        </div>
                        <h3 className="font-display font-semibold">Semaine {week}</h3>
                        <span className="text-xs text-muted-foreground">{doneInWeek}/{steps.length} terminé</span>
                        <div className="flex-1 max-w-xs">
                          <Progress value={(doneInWeek / steps.length) * 100} className="h-1" />
                        </div>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {steps.map((step) => (
                          <StepCard key={step.id} step={step} onToggle={handleToggle} />
                        ))}
                      </div>
                    </div>
                  );
                })}
            </div>
          </>
        )}

        {!roadmap && !generating && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
            <Map className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 font-medium text-muted-foreground">Aucune roadmap générée</p>
            <p className="text-sm text-muted-foreground/60">Lance une analyse de gap puis génère ta roadmap ci-dessus</p>
          </div>
        )}
      </main>
    </>
  );
}
