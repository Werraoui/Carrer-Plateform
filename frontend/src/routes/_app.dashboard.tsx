import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { BarChart3, Map, FileEdit, MessageSquare, UploadCloud, Target, TrendingUp } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { listCVs } from "@/lib/api/cv";
import { getGapHistory } from "@/lib/api/gap";
import { listRoadmaps } from "@/lib/api/roadmap";

export const Route = createFileRoute("/_app/dashboard")({ component: Dashboard });

const quickLinks = [
  { icon: UploadCloud, label: "Upload CV", to: "/upload", color: "text-blue-500", bg: "bg-blue-500/10" },
  { icon: BarChart3, label: "Gap Analysis", to: "/gap", color: "text-rose-500", bg: "bg-rose-500/10" },
  { icon: Map, label: "Roadmap", to: "/roadmap", color: "text-violet-500", bg: "bg-violet-500/10" },
  { icon: FileEdit, label: "ATS Optimizer", to: "/cv-optimization", color: "text-amber-500", bg: "bg-amber-500/10" },
  { icon: MessageSquare, label: "Interview", to: "/interview", color: "text-green-500", bg: "bg-green-500/10" },
];

function Dashboard() {
  const { user } = useAuth();
  const [cvCount, setCvCount] = useState<number | null>(null);
  const [latestGap, setLatestGap] = useState<any>(null);
  const [latestRoadmap, setLatestRoadmap] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      listCVs(),
      getGapHistory(),
      listRoadmaps(),
    ]).then(([cvRes, gapRes, roadmapRes]) => {
      if (cvRes.status === "fulfilled") setCvCount(cvRes.value.length);
      if (gapRes.status === "fulfilled" && gapRes.value.length > 0)
        setLatestGap(gapRes.value[gapRes.value.length - 1]);
      if (roadmapRes.status === "fulfilled" && roadmapRes.value.length > 0)
        setLatestRoadmap(roadmapRes.value[0]);
    }).finally(() => setLoading(false));
  }, []);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Bonjour" : hour < 18 ? "Bon après-midi" : "Bonsoir";

  const completedSteps = latestRoadmap?.steps?.filter((s: any) => s.status === "completed").length ?? 0;
  const totalSteps = latestRoadmap?.steps?.length ?? 0;
  const roadmapPct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

  return (
    <>
      <Topbar title="Dashboard" />
      <main className="mx-auto max-w-[1200px] space-y-6 p-4 md:p-8">

        {/* Hero welcome */}
        <div className="rounded-2xl border bg-gradient-to-br from-primary/10 via-secondary/5 to-transparent p-6 md:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-2xl font-bold md:text-3xl">
                {greeting}, {user?.name?.split(" ")[0] ?? "là"} 👋
              </h2>
              <p className="mt-1 text-muted-foreground">
                Voici ton espace CareerPlatform. Prêt·e à avancer ?
              </p>
            </div>
            <Link to="/upload">
              <Button size="lg">
                <UploadCloud className="mr-2 h-4 w-4" /> Upload un CV
              </Button>
            </Link>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "CVs uploadés", value: loading ? "—" : String(cvCount ?? 0), icon: UploadCloud, color: "text-blue-500" },
            { label: "Score employabilité", value: loading ? "—" : latestGap ? `${Math.round(latestGap.employability_score)}%` : "—", icon: Target, color: "text-rose-500" },
            { label: "Compétences manquantes", value: loading ? "—" : latestGap ? String(latestGap.missing_skills?.length ?? 0) : "—", icon: BarChart3, color: "text-amber-500" },
            { label: "Roadmap complétée", value: loading ? "—" : latestRoadmap ? `${roadmapPct}%` : "—", icon: TrendingUp, color: "text-green-500" },
          ].map((stat) => (
            <Card key={stat.label} className="shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <div className={`rounded-lg bg-muted p-2 ${stat.color}`}>
                    <stat.icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="font-display text-xl font-bold">{stat.value}</div>
                    <div className="text-xs text-muted-foreground">{stat.label}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {/* Quick navigation */}
          <Card className="shadow-sm lg:col-span-1">
            <CardHeader><CardTitle className="text-base">Accès rapide</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {quickLinks.map((item) => (
                <Link key={item.to} to={item.to}
                  className="flex items-center gap-3 rounded-xl p-3 transition hover:bg-accent">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${item.bg}`}>
                    <item.icon className={`h-4 w-4 ${item.color}`} />
                  </div>
                  <span className="font-medium text-sm">{item.label}</span>
                </Link>
              ))}
            </CardContent>
          </Card>

          {/* Latest gap */}
          <Card className="shadow-sm lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Dernière analyse de gap</CardTitle>
            </CardHeader>
            <CardContent>
              {latestGap ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Score d'employabilité</span>
                    <span className="font-display text-2xl font-bold text-primary">
                      {Math.round(latestGap.employability_score)}<span className="text-base font-normal text-muted-foreground">/100</span>
                    </span>
                  </div>
                  <Progress value={latestGap.employability_score} className="h-2" />
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">Compétences acquises</p>
                      <div className="flex flex-wrap gap-1">
                        {(latestGap.acquired_skills ?? []).slice(0, 5).map((s: string) => (
                          <Badge key={s} variant="secondary" className="bg-success/10 text-success text-xs">{s}</Badge>
                        ))}
                        {(latestGap.acquired_skills?.length ?? 0) > 5 && (
                          <Badge variant="outline" className="text-xs">+{latestGap.acquired_skills.length - 5}</Badge>
                        )}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">Compétences manquantes</p>
                      <div className="flex flex-wrap gap-1">
                        {(latestGap.missing_skills ?? []).slice(0, 5).map((s: string) => (
                          <Badge key={s} variant="secondary" className="bg-destructive/10 text-destructive text-xs">{s}</Badge>
                        ))}
                        {(latestGap.missing_skills?.length ?? 0) > 5 && (
                          <Badge variant="outline" className="text-xs">+{latestGap.missing_skills.length - 5}</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <Link to="/gap">
                    <Button variant="outline" size="sm">Voir l'analyse complète →</Button>
                  </Link>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <BarChart3 className="h-10 w-10 text-muted-foreground/40" />
                  <p className="mt-3 text-sm font-medium text-muted-foreground">Aucune analyse effectuée</p>
                  <Link to="/gap" className="mt-3">
                    <Button size="sm">Lancer une analyse</Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Roadmap progress */}
        {latestRoadmap && (
          <Card className="shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Ma roadmap — {latestRoadmap.job_name}</CardTitle>
              <Link to="/roadmap">
                <Button variant="outline" size="sm">Voir tout →</Button>
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{completedSteps}/{totalSteps} étapes complétées</span>
                <span className="font-semibold text-primary">{roadmapPct}%</span>
              </div>
              <Progress value={roadmapPct} className="h-2" />
              <div className="flex flex-wrap gap-2 pt-1">
                {(latestRoadmap.steps ?? []).slice(0, 6).map((s: any) => (
                  <Badge
                    key={s.id}
                    variant="secondary"
                    className={s.status === "completed"
                      ? "bg-success/10 text-success"
                      : "bg-muted text-muted-foreground"}
                  >
                    S{s.week_number} · {s.skill_name ?? s.title?.slice(0, 20)}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </>
  );
}
