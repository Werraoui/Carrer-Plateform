import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, X, AlertTriangle, Lightbulb, Loader2, FileEdit } from "lucide-react";
import { toast } from "sonner";
import { listCVs, type CVResponse } from "@/lib/api/cv";
import { optimizeCV, type ATSResult } from "@/lib/api/ats";

export const Route = createFileRoute("/_app/cv-optimization")({ component: CVOptimization });

function ScoreRing({ value, label }: { value: number; label: string }) {
  const color = value >= 75 ? "text-success" : value >= 50 ? "text-warning" : "text-destructive";
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`font-display text-3xl font-bold ${color}`}>{value}<span className="text-base font-normal text-muted-foreground">/100</span></div>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function CVOptimization() {
  const [cvs, setCvs] = useState<CVResponse[]>([]);
  const [selectedCv, setSelectedCv] = useState<string>("");
  const [offerText, setOfferText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ATSResult | null>(null);

  useEffect(() => {
    listCVs().then(setCvs).catch(() => {});
  }, []);

  async function handleAnalyze() {
    if (!selectedCv) return toast.error("Sélectionne un CV.");
    setLoading(true);
    try {
      const res = await optimizeCV(Number(selectedCv), offerText || undefined);
      setResult(res);
      toast.success(`Score ATS : ${res.ats_score}/100`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Erreur lors de l'analyse ATS.");
    } finally {
      setLoading(false);
    }
  }

  const scoreColor = (v: number) =>
    v >= 75 ? "bg-success" : v >= 50 ? "bg-warning" : "bg-destructive";

  return (
    <>
      <Topbar title="ATS Optimizer" />
      <main className="mx-auto max-w-[1100px] space-y-6 p-4 md:p-8">

        {/* Input */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Analyser ton CV</CardTitle>
            <CardDescription>Obtiens un score ATS et des suggestions concrètes</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Ton CV</label>
              <Select value={selectedCv} onValueChange={setSelectedCv}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un CV..." />
                </SelectTrigger>
                <SelectContent>
                  {cvs.length === 0 && <SelectItem value="none" disabled>Aucun CV — upload d'abord</SelectItem>}
                  {cvs.map((cv) => (
                    <SelectItem key={cv.id} value={String(cv.id)}>
                      {cv.file_path.split("/").pop()} · {new Date(cv.uploaded_at).toLocaleDateString()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description de l'offre <span className="text-muted-foreground">(optionnel)</span></label>
              <Textarea
                placeholder="Colle ici la description de l'offre de stage pour une analyse ciblée..."
                className="min-h-[100px]"
                value={offerText}
                onChange={(e) => setOfferText(e.target.value)}
              />
            </div>
            <Button onClick={handleAnalyze} disabled={loading} className="w-full sm:w-auto">
              {loading
                ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Analyse en cours...</>
                : "Analyser mon CV"}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        {result && (
          <>
            {/* Score overview */}
            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-base">Score global ATS</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4 flex flex-wrap items-center gap-8 justify-around">
                  <ScoreRing value={Math.round(result.ats_score)} label="Score global" />
                  <ScoreRing value={Math.round(result.keyword_score ?? 0)} label="Mots-clés" />
                  <ScoreRing value={Math.round(result.completeness_score ?? 0)} label="Complétude" />
                  <ScoreRing value={Math.round(result.format_score ?? 0)} label="Format" />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Score ATS</span>
                    <span className="font-medium">{Math.round(result.ats_score)}/100</span>
                  </div>
                  <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${scoreColor(result.ats_score)}`}
                      style={{ width: `${result.ats_score}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              {/* Keywords found */}
              <Card className="shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <CheckCircle2 className="h-4 w-4 text-success" /> Mots-clés trouvés
                  </CardTitle>
                  <CardDescription>{result.matched_keywords?.length ?? 0} correspondances</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  {(result.matched_keywords ?? []).map((k) => (
                    <Badge key={k} variant="secondary" className="bg-success/10 text-success">{k}</Badge>
                  ))}
                  {(!result.matched_keywords?.length) && (
                    <p className="text-sm text-muted-foreground">Aucun mot-clé correspondant détecté.</p>
                  )}
                </CardContent>
              </Card>

              {/* Missing keywords */}
              <Card className="shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <X className="h-4 w-4 text-destructive" /> Mots-clés manquants
                  </CardTitle>
                  <CardDescription>{result.missing_keywords?.length ?? 0} à ajouter</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  {(result.missing_keywords ?? []).map((k) => (
                    <Badge key={k} variant="secondary" className="bg-destructive/10 text-destructive">{k}</Badge>
                  ))}
                  {(!result.missing_keywords?.length) && (
                    <p className="text-sm text-muted-foreground">Aucun mot-clé manquant !</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Warnings */}
            {result.warnings?.length > 0 && (
              <Card className="shadow-sm border-warning/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <AlertTriangle className="h-4 w-4 text-warning" /> Avertissements
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {result.warnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-2 rounded-lg bg-warning/5 px-3 py-2 text-sm text-warning">
                      <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />{w}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Suggestions */}
            {result.suggestions?.length > 0 && (
              <Card className="shadow-sm border-primary/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Lightbulb className="h-4 w-4 text-primary" /> Suggestions d'amélioration
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {result.suggestions.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 rounded-lg bg-primary/5 px-3 py-2 text-sm">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">{i + 1}</span>
                      <span>{s}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </>
        )}

        {!result && !loading && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
            <FileEdit className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 font-medium text-muted-foreground">Analyse ton CV pour recevoir un score ATS</p>
            <p className="text-sm text-muted-foreground/60">Sélectionne ton CV ci-dessus et lance l'analyse</p>
          </div>
        )}
      </main>
    </>
  );
}
