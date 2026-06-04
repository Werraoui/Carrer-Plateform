import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MessageSquare, ChevronRight, ChevronLeft, Loader2, Trophy } from "lucide-react";
import { toast } from "sonner";
import { startInterview, type InterviewQuestion } from "@/lib/api/interview";
import { getMyTargetJobs, type UserTargetJobOut } from "@/lib/api/gap";

export const Route = createFileRoute("/_app/interview")({ component: Interview });

function Interview() {
  const [targetJobs, setTargetJobs] = useState<UserTargetJobOut[]>([]);
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [numQ, setNumQ] = useState<string>("5");
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [current, setCurrent] = useState(0);
  const [revealed, setRevealed] = useState<Set<number>>(new Set());
  const [done, setDone] = useState(false);

  useEffect(() => {
    getMyTargetJobs().then(setTargetJobs).catch(() => {});
  }, []);

  async function handleStart() {
    if (!selectedJob) return toast.error("Sélectionne un métier cible.");
    setLoading(true);
    setDone(false);
    setCurrent(0);
    setRevealed(new Set());
    try {
      const res = await startInterview(Number(selectedJob), Number(numQ));
      setQuestions(res.questions);
      toast.success(`${res.questions.length} questions générées !`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Erreur lors de la génération.");
    } finally {
      setLoading(false);
    }
  }

  function revealAnswer(i: number) {
    setRevealed((prev) => new Set([...prev, i]));
  }

  function next() {
    if (current < questions.length - 1) {
      setCurrent((c) => c + 1);
    } else {
      setDone(true);
    }
  }

  function restart() {
    setQuestions([]);
    setDone(false);
    setCurrent(0);
    setRevealed(new Set());
  }

  const q = questions[current];

  return (
    <>
      <Topbar title="Interview Simulator" />
      <main className="mx-auto max-w-[900px] space-y-6 p-4 md:p-8">

        {/* Config */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Simuler un entretien technique</CardTitle>
            <CardDescription>Des questions générées par IA basées sur ton métier cible</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px] space-y-1.5">
              <label className="text-sm font-medium">Métier cible</label>
              <Select value={selectedJob} onValueChange={setSelectedJob}>
                <SelectTrigger><SelectValue placeholder="Choisir..." /></SelectTrigger>
                <SelectContent>
                  {targetJobs.length === 0 && (
                    <SelectItem value="none" disabled>Aucun métier — configure d'abord</SelectItem>
                  )}
                  {targetJobs.map((j) => (
                    <SelectItem key={j.id} value={String(j.id)}>
                      {j.target_job?.name ?? `Job #${j.target_job_id}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[140px] space-y-1.5">
              <label className="text-sm font-medium">Nombre de questions</label>
              <Select value={numQ} onValueChange={setNumQ}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[3, 5, 8, 10].map((n) => (
                    <SelectItem key={n} value={String(n)}>{n} questions</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleStart} disabled={loading}>
              {loading
                ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Génération...</>
                : "Commencer"}
            </Button>
          </CardContent>
        </Card>

        {/* Done screen */}
        {done && (
          <div className="flex flex-col items-center justify-center rounded-2xl border bg-gradient-to-br from-primary/5 to-secondary/5 py-16 text-center">
            <Trophy className="h-16 w-16 text-primary" />
            <h2 className="mt-4 font-display text-2xl font-bold">Simulation terminée !</h2>
            <p className="mt-2 text-muted-foreground">Tu as répondu à {questions.length} questions techniques.</p>
            <Button className="mt-6" onClick={restart}>Recommencer</Button>
          </div>
        )}

        {/* Question card */}
        {!done && questions.length > 0 && q && (
          <div className="space-y-4">
            {/* Progress */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MessageSquare className="h-4 w-4" />
              Question {current + 1} / {questions.length}
              <div className="ml-2 flex-1 max-w-xs">
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-300"
                    style={{ width: `${((current + 1) / questions.length) * 100}%` }}
                  />
                </div>
              </div>
              {q.related_skill && <Badge variant="outline">{q.related_skill}</Badge>}
            </div>

            <Card className="shadow-sm">
              <CardContent className="pt-6">
                <p className="font-display text-lg font-semibold leading-snug">{q.question_text}</p>

                {!revealed.has(current) ? (
                  <Button
                    variant="outline"
                    className="mt-6"
                    onClick={() => revealAnswer(current)}
                  >
                    Voir un élément de réponse
                  </Button>
                ) : (
                  <div className="mt-6 rounded-xl border-l-4 border-primary bg-primary/5 p-4 text-sm text-muted-foreground">
                    <p className="font-medium text-foreground mb-1">Éléments de réponse attendus :</p>
                    <p>
                      Réfléchis aux concepts clés liés à{" "}
                      <span className="font-medium text-primary">{q.related_skill ?? "ce sujet"}</span>.
                      Sois précis·e, donne des exemples concrets et explique le raisonnement derrière.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="flex items-center justify-between">
              <Button
                variant="outline"
                onClick={() => setCurrent((c) => Math.max(0, c - 1))}
                disabled={current === 0}
              >
                <ChevronLeft className="mr-1 h-4 w-4" /> Précédent
              </Button>
              <Button onClick={next}>
                {current === questions.length - 1 ? "Terminer" : "Suivant"}
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* All questions list (side) */}
        {!done && questions.length > 0 && (
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm">Toutes les questions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {questions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => { setCurrent(i); setDone(false); }}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm transition hover:bg-accent ${i === current ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground"}`}
                >
                  <span className="mr-2 text-xs opacity-60">Q{i + 1}</span>
                  {q.question_text.slice(0, 70)}{q.question_text.length > 70 ? "…" : ""}
                </button>
              ))}
            </CardContent>
          </Card>
        )}

        {!loading && questions.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
            <MessageSquare className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 font-medium text-muted-foreground">Aucune simulation en cours</p>
            <p className="text-sm text-muted-foreground/60">Configure et lance ton entretien ci-dessus</p>
          </div>
        )}
      </main>
    </>
  );
}
