import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Stethoscope, CheckCircle, XCircle, Clock, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { listExtractions } from "@/lib/api";
import type { ExtractionResponse } from "@/types/nameboard";

function statusBadge(status: string) {
  if (status === "ACCEPTED") return <Badge variant="success" className="flex items-center gap-1"><CheckCircle className="w-3 h-3" />Accepted</Badge>;
  if (status === "REJECTED") return <Badge variant="danger" className="flex items-center gap-1"><XCircle className="w-3 h-3" />Rejected</Badge>;
  return <Badge variant="warning" className="flex items-center gap-1"><Clock className="w-3 h-3" />Pending</Badge>;
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const [extractions, setExtractions] = useState<ExtractionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listExtractions()
      .then(setExtractions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center gap-3 sticky top-0 z-10">
        <Button variant="ghost" size="icon" onClick={() => navigate("/upload")}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-primary rounded-md flex items-center justify-center">
            <Stethoscope className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-semibold">Extraction History</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8">
        {loading && (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="text-center py-16 text-muted-foreground">
            {error === "Failed to load extractions" && error.includes("401")
              ? "Please log in to view your history."
              : error}
          </div>
        )}

        {!loading && !error && extractions.length === 0 && (
          <div className="text-center py-16 text-muted-foreground">
            <p className="text-lg font-medium">No extractions yet</p>
            <p className="text-sm mt-1">Upload a nameboard to get started.</p>
            <Button className="mt-4" onClick={() => navigate("/upload")}>Upload now</Button>
          </div>
        )}

        {!loading && extractions.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">{extractions.length} extraction{extractions.length !== 1 ? "s" : ""}</p>
            {extractions.map((ex) => {
              const d = ex.extracted_data;
              const name = d.doctor_name?.value ?? "—";
              const clinic = d.clinic_name?.value ?? "";
              const conf = Math.round(ex.overall_confidence * 100);
              const confVariant = ex.overall_confidence >= 0.85 ? "success" : ex.overall_confidence >= 0.70 ? "warning" : "danger";

              return (
                <Card
                  key={ex.id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => navigate(`/review/${ex.id}`)}
                >
                  <CardContent className="pt-4 pb-4 flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-medium text-sm truncate">{name}</p>
                        {statusBadge(ex.status)}
                      </div>
                      {clinic && <p className="text-xs text-muted-foreground mt-0.5 truncate">{clinic}</p>}
                      <p className="text-xs text-muted-foreground mt-1">{formatDate(ex.created_at as unknown as string)}</p>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <Badge variant={confVariant}>{conf}%</Badge>
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
