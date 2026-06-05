import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Bot, Loader2, Send, User, Trophy } from "lucide-react";
import { toast } from "sonner";
import {
  sendInterviewMessage,
  type ChatMessage,
  type InterviewFinalReport,
  type McqQuestion,
} from "@/lib/api/interview";
import { formatApiError } from "@/lib/api/client";

export const Route = createFileRoute("/_app/interview")({ component: Interview });

function Interview() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mcq, setMcq] = useState<McqQuestion | null>(null);
  const [openQuestion, setOpenQuestion] = useState<string | null>(null);
  const [questionType, setQuestionType] = useState<string | null>(null);
  const [complete, setComplete] = useState(false);
  const [finalReport, setFinalReport] = useState<InterviewFinalReport | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading, finalReport]);

  function applyResponse(res: Awaited<ReturnType<typeof sendInterviewMessage>>) {
    setSessionId(res.session_id);
    setHistory(res.history);
    setMcq(res.mcq ?? null);
    setOpenQuestion(res.open_question ?? null);
    setQuestionType(res.question_type ?? null);
    setComplete(res.interview_complete);
    setFinalReport(res.final_report ?? null);
  }

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading || complete) return;
    setLoading(true);
    setInput("");
    try {
      const res = await sendInterviewMessage(trimmed, sessionId);
      applyResponse(res);
    } catch (err) {
      toast.error(formatApiError(err, "Erreur lors de l'entretien."));
    } finally {
      setLoading(false);
    }
  }

  function handleMcqChoice(choice: string) {
    const letter = choice.trim().charAt(0).toUpperCase();
    sendMessage(letter.length === 1 && /[A-D]/.test(letter) ? letter : choice);
  }

  function restart() {
    setSessionId(null);
    setHistory([]);
    setInput("");
    setMcq(null);
    setOpenQuestion(null);
    setQuestionType(null);
    setComplete(false);
    setFinalReport(null);
  }

  const starterHint =
    "Collez ici l'offre LinkedIn/Indeed (titre, entreprise, missions, stack…) puis envoyez. " +
    "Exemple : « Voici l'offre : … Je veux simuler un entretien technique en QCM et questions ouvertes. »";

  return (
    <>
      <Topbar title="Interview Simulator" />
      <main className="mx-auto flex max-w-[900px] flex-col gap-4 p-4 md:p-6" style={{ minHeight: "calc(100vh - 4rem)" }}>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Entretien simulé (Gemini)</CardTitle>
            <CardDescription>
              Collez une offre, répondez aux QCM (A–D) et aux questions ouvertes. Bilan avec score à la fin.
            </CardDescription>
          </CardHeader>
        </Card>

        {/* Chat */}
        <Card className="flex flex-1 flex-col shadow-sm">
          <CardContent className="flex flex-1 flex-col gap-4 p-4 pt-4">
            <div className="flex-1 space-y-4 overflow-y-auto pr-1" style={{ maxHeight: "55vh" }}>
              {history.length === 0 && !loading && (
                <div className="rounded-xl border border-dashed bg-muted/30 p-4 text-sm text-muted-foreground">
                  {starterHint}
                </div>
              )}

              {history.map((msg, i) => (
                <div
                  key={i}
                  className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                      msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                    }`}
                  >
                    {msg.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                  </div>
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> L'interviewer réfléchit…
                </div>
              )}

              {/* MCQ buttons */}
              {!complete && !loading && mcq && questionType === "mcq" && (
                <div className="space-y-2 rounded-xl border bg-card p-4">
                  <p className="text-sm font-medium">{mcq.question}</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {mcq.choices.map((c) => (
                      <Button
                        key={c}
                        variant="outline"
                        className="h-auto justify-start whitespace-normal py-2 text-left text-sm"
                        onClick={() => handleMcqChoice(c)}
                      >
                        {c}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {!complete && !loading && questionType === "open" && openQuestion && (
                <p className="text-xs text-muted-foreground">
                  Question ouverte — répondez dans le champ ci-dessous (3–6 phrases).
                </p>
              )}

              {/* Final report */}
              {complete && finalReport && (
                <div className="space-y-4 rounded-xl border border-primary/30 bg-primary/5 p-5">
                  <div className="flex items-center gap-3">
                    <Trophy className="h-8 w-8 text-primary" />
                    <div>
                      <p className="font-display text-2xl font-bold">{finalReport.score_percent}/100</p>
                      <Badge variant="secondary">{finalReport.score_label}</Badge>
                    </div>
                  </div>
                  <p className="text-sm">{finalReport.summary}</p>
                  <p className="text-sm font-medium text-primary">{finalReport.overall_advice}</p>
                  {finalReport.answers_review.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-semibold">Détail des réponses</p>
                      {finalReport.answers_review.map((r) => (
                        <div key={r.question_number} className="rounded-lg border bg-background p-3 text-sm">
                          <p className="font-medium">
                            Q{r.question_number} — {r.is_correct ? "✓" : "✗"} {r.question_text}
                          </p>
                          <p className="mt-1 text-muted-foreground">{r.feedback}</p>
                          {r.improvement && (
                            <p className="mt-1 text-primary">{r.improvement}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  <Button onClick={restart}>Nouvel entretien</Button>
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            {/* Input */}
            {!complete && (
              <div className="flex gap-2 border-t pt-4">
                {history.length === 0 ? (
                  <Textarea
                    placeholder={starterHint}
                    className="min-h-[80px] flex-1 resize-none"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={loading}
                  />
                ) : (
                  <Input
                    placeholder={
                      questionType === "open"
                        ? "Votre réponse…"
                        : mcq
                          ? "Ou tapez A, B, C, D…"
                          : "Votre message…"
                    }
                    className="flex-1"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage(input))}
                    disabled={loading}
                  />
                )}
                <Button
                  size="icon"
                  className="shrink-0"
                  disabled={loading || !input.trim()}
                  onClick={() => sendMessage(input)}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </>
  );
}
