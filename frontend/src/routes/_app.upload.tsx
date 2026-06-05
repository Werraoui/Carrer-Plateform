import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useRef } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { UploadCloud, FileText, CheckCircle2, Sparkles } from "lucide-react";
import { uploadCV } from "@/lib/api/cv";
import { formatApiError } from "@/lib/api/client";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/upload")({ component: UploadCV });

function UploadCV() {
  const nav = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [stage, setStage] = useState<"idle" | "uploading" | "done">("idle");
  const [progress, setProgress] = useState(0);
  const [fileName, setFileName] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [cvId, setCvId] = useState<number | null>(null);
  const [uploadMessage, setUploadMessage] = useState("");

  async function handleFile(file: File) {
    setFileName(file.name);
    setStage("uploading");
    setProgress(0);

    // Fake progress animation
    const timer = setInterval(() => {
      setProgress((p) => (p >= 85 ? p : p + 10));
    }, 200);

    try {
      const res = await uploadCV(file);
      clearInterval(timer);
      setProgress(100);
      setSkills(res.skills);
      setCvId(res.cv_id);
      setUploadMessage(res.message);
      setStage("done");
      if (res.skill_count > 0) {
        toast.success(`CV uploadé ! ${res.skill_count} compétences extraites.`);
      } else {
        toast.warning(res.message);
      }
    } catch (err: any) {
      clearInterval(timer);
      setStage("idle");
      toast.error(formatApiError(err, "Erreur lors de l'upload."));
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <>
      <Topbar title="Upload CV" />
      <main className="space-y-6 p-4 md:p-6">
        <Card className="shadow-soft">
          <CardHeader>
            <CardTitle>Upload your CV</CardTitle>
            <CardDescription>We accept PDF and DOCX up to 10 MB</CardDescription>
          </CardHeader>
          <CardContent>
            <input ref={inputRef} type="file" accept=".pdf,.docx,.doc" className="hidden" onChange={onFileChange} />
            <div
              onDrop={onDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => stage === "idle" && inputRef.current?.click()}
              className="group flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-muted/30 p-12 transition hover:border-primary hover:bg-primary/5"
            >
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary transition group-hover:scale-110">
                <UploadCloud className="h-8 w-8" />
              </div>
              <p className="mt-4 font-display text-lg font-semibold">Drag & drop your CV here</p>
              <p className="text-sm text-muted-foreground">or click to browse — PDF / DOCX</p>
              <div className="mt-4 flex gap-2">
                <Badge variant="outline">PDF</Badge>
                <Badge variant="outline">DOCX</Badge>
                <Badge variant="outline">Max 10 MB</Badge>
              </div>
            </div>

            {stage !== "idle" && (
              <div className="mt-6 rounded-xl border bg-card p-4">
                <div className="flex items-center gap-3">
                  <FileText className="h-6 w-6 text-primary" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{fileName}</p>
                      <span className="text-xs text-muted-foreground">
                        {stage === "uploading" ? `${progress}%` : "Prêt"}
                      </span>
                    </div>
                    <Progress value={progress} className="mt-2 h-1.5" />
                  </div>
                  {stage === "done" && <CheckCircle2 className="h-5 w-5 text-success" />}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {stage === "done" && (
          <Card className="shadow-soft">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <CardTitle>Compétences extraites</CardTitle>
              </div>
              <CardDescription>Notre IA a détecté {skills.length} compétences dans ton CV</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {skills.length > 0 ? (
                  skills.map((s) => (
                    <Badge key={s} className="bg-primary/10 text-primary hover:bg-primary/20" variant="secondary">
                      {s}
                    </Badge>
                  ))
                ) : (
                  <div className="space-y-2 rounded-lg border border-warning/40 bg-warning/10 p-4 text-sm text-muted-foreground">
                    <p className="font-medium text-foreground">Aucune compétence détectée</p>
                    <p>{uploadMessage}</p>
                    <p>Sur Render (plan gratuit), le service ML peut mettre ~30 s à démarrer. Ré-uploadez le CV après ce délai.</p>
                  </div>
                )}
              </div>
              <Button className="mt-6 h-11" onClick={() => nav({ to: "/gap" })}>
                Analyser le gap →
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </>
  );
}
