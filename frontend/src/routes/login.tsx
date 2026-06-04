import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { GraduationCap, Mail, Lock, User, FileSearch, Target, Map as MapIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { login, register } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth-context";

export const Route = createFileRoute("/login")({ component: AuthPage });

const features = [
  { icon: FileSearch, title: "Analyse de CV", desc: "Extraction automatique de tes compétences." },
  { icon: Target, title: "Skill Gap", desc: "Compare ton profil au marché tech." },
  { icon: MapIcon, title: "Roadmap personnalisée", desc: "Un plan d'action semaine par semaine." },
];

function AuthPage() {
  const nav = useNavigate();
  const { setAuth } = useAuth();
  const [tab, setTab] = useState<"login" | "register">("login");

  // Login state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPass, setLoginPass] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // Register state
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPass, setRegPass] = useState("");
  const [regLevel, setRegLevel] = useState("bac3");
  const [regLoading, setRegLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginLoading(true);
    try {
      const res = await login(loginEmail, loginPass);
      setAuth(res.access_token, res.user);
      toast.success(`Bienvenue, ${res.user.name} !`);
      nav({ to: "/dashboard" });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Email ou mot de passe incorrect.");
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setRegLoading(true);
    try {
      const res = await register(regName, regEmail, regPass, regLevel);
      setAuth(res.access_token, res.user);
      toast.success("Compte créé ! Bienvenue 🎉");
      nav({ to: "/dashboard" });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Erreur lors de la création du compte.");
    } finally {
      setRegLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Left panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-[#0F172A] via-[#1E1B4B] to-[#312E81] p-10 text-white lg:flex">
        <div className="flex items-center gap-2 relative z-10">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg">
            <GraduationCap className="h-5 w-5" />
          </div>
          <span className="font-display text-xl font-bold">CareerPlatform</span>
        </div>
        <div className="relative z-10 max-w-md space-y-8">
          <div>
            <h2 className="font-display text-4xl font-bold leading-tight">Prépare ton futur tech.</h2>
            <p className="mt-3 text-base text-white/70">L'IA qui transforme ton CV en plan de carrière concret.</p>
          </div>
          <div className="space-y-4">
            {features.map((f) => (
              <div key={f.title} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/20 text-primary-foreground">
                  <f.icon className="h-5 w-5" />
                </div>
                <div>
                  <div className="font-semibold">{f.title}</div>
                  <div className="text-sm text-white/65">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="absolute -right-32 -top-32 h-96 w-96 rounded-full bg-primary/30 blur-3xl" />
        <div className="absolute -bottom-32 -left-32 h-96 w-96 rounded-full bg-secondary/30 blur-3xl" />
        <p className="relative z-10 text-xs text-white/40">© 2026 CareerPlatform.</p>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6 lg:p-12 bg-background">
        <div className="w-full max-w-md rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
          <div className="mb-6 flex items-center gap-2 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <GraduationCap className="h-4 w-4" />
            </div>
            <span className="font-display text-lg font-bold">CareerPlatform</span>
          </div>

          <Tabs value={tab} onValueChange={(v) => setTab(v as any)} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">Se connecter</TabsTrigger>
              <TabsTrigger value="register">S'inscrire</TabsTrigger>
            </TabsList>

            {/* LOGIN */}
            <TabsContent value="login" className="mt-6">
              <div className="mb-5">
                <h1 className="font-display text-2xl font-bold">Bon retour 👋</h1>
                <p className="mt-1 text-sm text-muted-foreground">Connecte-toi pour continuer.</p>
              </div>
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="lemail">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="lemail" type="email" className="pl-10" placeholder="toi@exemple.com"
                      value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} required />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lpass">Mot de passe</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="lpass" type="password" className="pl-10"
                      value={loginPass} onChange={(e) => setLoginPass(e.target.value)} required />
                  </div>
                </div>
                <Button type="submit" className="h-11 w-full text-base" disabled={loginLoading}>
                  {loginLoading ? "Connexion..." : "Se connecter"}
                </Button>
              </form>
            </TabsContent>

            {/* REGISTER */}
            <TabsContent value="register" className="mt-6">
              <div className="mb-5">
                <h1 className="font-display text-2xl font-bold">Créer mon compte</h1>
                <p className="mt-1 text-sm text-muted-foreground">Commence ton parcours en 30 secondes.</p>
              </div>
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="rname">Nom complet</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="rname" className="pl-10" placeholder="Sarah Chen"
                      value={regName} onChange={(e) => setRegName(e.target.value)} required />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="remail">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="remail" type="email" className="pl-10" placeholder="toi@exemple.com"
                      value={regEmail} onChange={(e) => setRegEmail(e.target.value)} required />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rpass">Mot de passe</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input id="rpass" type="password" className="pl-10"
                      value={regPass} onChange={(e) => setRegPass(e.target.value)} required />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rlevel">Niveau d'études</Label>
                  <Select value={regLevel} onValueChange={setRegLevel}>
                    <SelectTrigger id="rlevel"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="bac2">Bac+2</SelectItem>
                      <SelectItem value="bac3">Bac+3</SelectItem>
                      <SelectItem value="bac5">Bac+5</SelectItem>
                      <SelectItem value="bootcamp">Bootcamp</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button type="submit" className="h-11 w-full text-base" disabled={regLoading}>
                  {regLoading ? "Création..." : "Créer mon compte"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
