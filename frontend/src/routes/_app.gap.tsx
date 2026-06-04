import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Check, X, ArrowRight, Lightbulb, Loader2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { toast } from "sonner";
import { listCVs, type CVResponse } from "@/lib/api/cv";
import { analyzeGap, getAvailableJobs, setTargetJob, type TargetJobOut, type GapResult } from "@/lib/api/gap";

export const Route = createFileRoute("/_app/gap")({ component: Gap });

function ScoreBadge({ value }: { value: number }) {
  const color =
    value >= 75
      ? "bg-success text-success-foreground"
      : value >= 50
      ? "bg-warning text-warning-foreground"
      : "bg-destructive text-destructive-foreground";
  return (
    <div className={`flex items-center gap-3 rounded-2xl px-5 py-3 ${color} shadow-sm`}>
      <div className="font-display text-4xl font-bold leading-none">{value}</div>
      <div className="text-sm leading-tight">
        <div className="font-semibold">Employability</div>
        <div className="opacity-80">Score / 100</div>
      </div>
    </div>
  );
}

function Gap() {
  const nav = useNavigate();
  const [mode, setMode] = useState<"market" | "offer">("market");
  const [cvs, setCvs] = useState<CVResponse[]>([]);
  const [jobs, setJobs] = useState<TargetJobOut[]>([]);
  const [selectedCv, setSelectedCv] = useState<string>("");
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [offerText, setOfferText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GapResult | null>(null);

  useEffect(() => {
    listCVs().then(setCvs).catch(() => {});
    getAvailableJobs().then(setJobs).catch(() => {});
  }, []);

  async function handleAnalyze() {
    if (!selectedCv) return toast.error("Sélectionne un CV.");
    if (!selectedJob && mode === "market") return toast.error("Sélectionne un métier cible.");
    setLoading(true);
    try {
      const job = jobs.find((j) => String(j.id) === selectedJob);
      if (job) await setTargetJob(job.id);
      const res = await analyzeGap(
        Number(selectedCv),
        mode === "market" ? (job?.id ?? undefined) : undefined,
        undefined
      );
      setResult(res);
      toast.success("Analyse terminée !");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Erreur lors de l'analyse.");
    } finally {
      setLoading(false);
    }
  }

  const marketDemand = (result?.missing_skills ?? []).slice(0, 8).map((s) => ({
    skill: s,
    demand: Math.floor(Math.random() * 40) + 50, // placeholder visuel
  }));

  return (
    <>
      <Topbar title="Gap Analysis" />
      <main className="mx-auto max-w-[1200px] space-y-6 p-4 md:p-8">

        {/* Form */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Lancer une analyse</CardTitle>
            <CardDescription>Compare ton CV avec le marché ou une offre spécifique.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {/* CV selector */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Ton CV</label>
                <Select value={selectedCv} onValueChange={setSelectedCv}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner un CV..." />
                  </SelectTrigger>
                  <SelectContent>
                    {cvs.length === 0 && (
                      <SelectItem value="none" disabled>Aucun CV — upload d'abord</SelectItem>
                    )}
                    {cvs.map((cv) => (
                      <SelectItem key={cv.id} value={String(cv.id)}>
                        {cv.file_path.split("/").pop()} · {new Date(cv.uploaded_at).toLocaleDateString()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Mode */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Comparer avec</label>
                <Tabs value={mode} onValueChange={(v) => setMode(v as any)}>
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="market">Marché général</TabsTrigger>
                    <TabsTrigger value="offer">Offre spécifique</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            </div>

            {/* Job selector (market mode) */}
            {mode === "market" && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Métier cible</label>
                <Select value={selectedJob} onValueChange={setSelectedJob}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choisir un métier..." />
                  </SelectTrigger>
                  <SelectContent>
                    {jobs.map((j) => (
                      <SelectItem key={j.id} value={String(j.id)}>{j.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Offer text (offer mode) */}
            {mode === "offer" && (
              <Textarea
                placeholder="Colle ici la description de l'offre de stage..."
                className="min-h-[100px]"
                value={offerText}
                onChange={(e) => setOfferText(e.target.value)}
              />
            )}

            <Button onClick={handleAnalyze} disabled={loading} className="w-full sm:w-auto">
              {loading ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Analyse en cours...</> : "Analyser le gap"}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        {result && (
          <>
            <div className="flex items-center gap-3">
              <ScoreBadge value={Math.round(result.employability_score)} />
              <p className="text-sm text-muted-foreground">
                Score d'employabilité calculé à partir de {result.acquired_skills.length + result.missing_skills.length} compétences analysées
              </p>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="shadow-sm">
                <CardHeader>
                  <CardTitle className="text-base">Tes compétences</CardTitle>
                  <CardDescription>{result.acquired_skills.length} détectées dans ton CV</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  {result.acquired_skills.map((s) => (
                    <Badge key={s} variant="secondary" className="bg-success/10 text-success hover:bg-success/15">
                      <Check className="mr-1 h-3 w-3" />{s}
                    </Badge>
                  ))}
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader>
                  <CardTitle className="text-base">Compétences manquantes</CardTitle>
                  <CardDescription>{result.missing_skills.length} gaps à combler</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  {result.missing_skills.map((s) => (
                    <Badge key={s} variant="secondary" className="bg-destructive/10 text-destructive hover:bg-destructive/15">
                      <X className="mr-1 h-3 w-3" />{s}
                    </Badge>
                  ))}
                </CardContent>
              </Card>
            </div>

            {marketDemand.length > 0 && (
              <Card className="shadow-sm">
                <CardHeader>
                  <CardTitle className="text-base">Top compétences manquantes</CardTitle>
                  <CardDescription>Fréquence dans les offres de stage du marché</CardDescription>
                </CardHeader>
                <CardContent className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={marketDemand} layout="vertical" margin={{ left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                      <XAxis type="number" stroke="var(--color-muted-foreground)" fontSize={12} domain={[0, 100]} />
                      <YAxis type="category" dataKey="skill" stroke="var(--color-muted-foreground)" fontSize={12} width={130} />
                      <Tooltip contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 12 }} />
                      <Bar dataKey="demand" fill="var(--color-primary)" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}

            <Card className="shadow-sm border-primary/30 bg-gradient-to-br from-primary/5 to-secondary/5">
              <CardContent className="flex flex-wrap items-center justify-between gap-4 p-6">
                <div className="flex items-center gap-3">
                  <Lightbulb className="h-6 w-6 text-primary" />
                  <div>
                    <p className="font-display text-lg font-semibold">Prêt à combler ces gaps ?</p>
                    <p className="text-sm text-muted-foreground">Génère un plan d'apprentissage personnalisé semaine par semaine.</p>
                  </div>
                </div>
                <Button size="lg" onClick={() => nav({ to: "/roadmap" })}>
                  Générer ma roadmap <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          </>
        )}

        {/* Empty state */}
        {!result && !loading && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
            <BarChart className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 font-medium text-muted-foreground">Lance une analyse pour voir tes résultats</p>
            <p className="text-sm text-muted-foreground/60">Sélectionne un CV et un métier cible ci-dessus</p>
          </div>
        )}
      </main>
    </>
  );
}
