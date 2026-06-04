import { createFileRoute } from "@tanstack/react-router";
import { Topbar } from "@/components/topbar";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { MapPin, Calendar } from "lucide-react";
import { internships } from "@/lib/mock-data";

export const Route = createFileRoute("/_app/internships")({ component: Internships });

const matchTone = (m: number) => m >= 80 ? "bg-success/15 text-success" : m >= 70 ? "bg-warning/15 text-warning" : "bg-muted text-muted-foreground";

function Internships() {
  return (
    <>
      <Topbar title="Internship Matching" />
      <main className="space-y-6 p-4 md:p-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {internships.map(i => (
            <Card key={i.id} className="shadow-soft transition hover:-translate-y-0.5 hover:shadow-card">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3"><span className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted text-2xl">{i.logo}</span><div><p className="font-display font-semibold">{i.company}</p><p className="text-xs text-muted-foreground flex items-center gap-1"><MapPin className="h-3 w-3" />{i.location}</p></div></div>
                  <Badge className={matchTone(i.match)} variant="secondary">{i.match}% match</Badge>
                </div>
                <p className="mt-4 font-medium">{i.position}</p>
                <p className="mt-1 text-xs text-muted-foreground flex items-center gap-1"><Calendar className="h-3 w-3" />{i.type}</p>
                <Progress value={i.match} className="mt-4 h-1.5" />
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {i.skills.map(s => <Badge key={s} variant="outline" className="text-xs">{s}</Badge>)}
                </div>
                <div className="mt-5 flex gap-2"><Button className="flex-1">Apply</Button><Button variant="outline">Save</Button></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </>
  );
}
