import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LogOut, Trash2, FileText, Calendar } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { listCVs, deleteCV, type CVResponse } from "@/lib/api/cv";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/profile")({ component: Profile });

function Profile() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [cvs, setCvs] = useState<CVResponse[]>([]);

  useEffect(() => {
    listCVs().then(setCvs).catch(() => {});
  }, []);

  async function handleDelete(id: number) {
    try {
      await deleteCV(id);
      setCvs((prev) => prev.filter((c) => c.id !== id));
      toast.success("CV supprimé.");
    } catch {
      toast.error("Erreur lors de la suppression.");
    }
  }

  function handleLogout() {
    logout();
    nav({ to: "/login" });
  }

  const initials = user?.name
    ? user.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()
    : "?";

  return (
    <>
      <Topbar title="Profile" />
      <main className="mx-auto max-w-[800px] space-y-6 p-4 md:p-8">
        {/* User card */}
        <Card className="shadow-sm">
          <CardContent className="flex flex-wrap items-center gap-5 p-6">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-2xl font-bold text-primary-foreground shadow-md">
              {initials}
            </div>
            <div>
              <h2 className="font-display text-xl font-bold">{user?.name}</h2>
              <p className="text-muted-foreground">{user?.email}</p>
              <div className="mt-1 flex gap-2">
                {user?.level && <Badge variant="secondary">{user.level}</Badge>}
                <Badge variant="outline" className="text-xs">
                  <Calendar className="mr-1 h-3 w-3" />
                  Inscrit le {user?.created_at ? new Date(user.created_at).toLocaleDateString("fr-FR") : "—"}
                </Badge>
              </div>
            </div>
            <Button variant="destructive" size="sm" className="ml-auto" onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" /> Se déconnecter
            </Button>
          </CardContent>
        </Card>

        {/* CVs */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Mes CVs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {cvs.length === 0 && (
              <p className="text-sm text-muted-foreground">Aucun CV uploadé. Va dans Upload CV pour commencer.</p>
            )}
            {cvs.map((cv) => (
              <div key={cv.id} className="flex items-center gap-3 rounded-xl border bg-card p-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium text-sm">{cv.file_path.split("/").pop()}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(cv.uploaded_at).toLocaleDateString("fr-FR")}
                    {cv.skills_extracted?.length > 0 && ` · ${cv.skills_extracted.length} compétences`}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive hover:bg-destructive/10"
                  onClick={() => handleDelete(cv.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      </main>
    </>
  );
}
