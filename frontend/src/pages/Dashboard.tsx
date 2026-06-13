import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useDropzone } from "react-dropzone";
import { UploadCloud, File, AlertCircle, CheckCircle2, Loader2, LogOut, Download } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import ResultsDashboard from "@/components/ResultsDashboard";

export default function Dashboard() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [currentDatasetId, setCurrentDatasetId] = useState<string | null>(null);
  // ── new: interactive dashboard state ──────────────────────────────────────
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const { data: user } = useQuery({
    queryKey: ["user"],
    queryFn: async () => {
      const res = await api.get("/auth/me");
      return res.data;
    },
  });

  const { data: statusData } = useQuery({
    queryKey: ["status", currentDatasetId],
    queryFn: async () => {
      const res = await api.get(`/datasets/${currentDatasetId}/status`);
      return res.data;
    },
    enabled: !!currentDatasetId,
    refetchInterval: (data) => {
        // Stop polling if done or error
        if (data?.status === 'done' || data?.status === 'error') {
            return false;
        }
        return 2000; // Poll every 2s
    },
  });

  const onDrop = async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    setError("");
    setUploading(true);

    const formData = new FormData();
    acceptedFiles.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const res = await api.post("/datasets/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setCurrentDatasetId(res.data.id);

      // ── call /api/analyze for the interactive on-screen dashboard ────────
      setAnalyzing(true);
      try {
        const singleFile = acceptedFiles[0];
        const analyzeForm = new FormData();
        analyzeForm.append("file", singleFile);
        const analyzeRes = await api.post("/analyze", analyzeForm, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        setAnalysisResult(analyzeRes.data);
      } catch {
        // non-fatal: PDF pipeline continues even if analyze fails
      } finally {
        setAnalyzing(false);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to upload files.");
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.ms-excel": [".csv"],
    },
    maxSize: 500 * 1024 * 1024, // 500MB
  });

  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

  const handleDownload = async () => {
    if (!currentDatasetId) return;
    setDownloading(true);
    try {
      // Use Axios so the JWT token is sent in the Authorization header
      const response = await api.get(`/reports/${currentDatasetId}/download`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `RetailSense_Report_${currentDatasetId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to download report.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/50 backdrop-blur sticky top-0 z-10">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary font-bold">
              R
            </div>
            <span className="font-semibold tracking-tight text-lg">RetailSense</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground hidden md:inline-block">
              {user?.email}
            </span>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {!currentDatasetId ? (
          <div className="max-w-3xl mx-auto mt-10">
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold mb-2">Upload Sales Data</h1>
              <p className="text-muted-foreground">Drag and drop one or multiple CSV files to generate your enterprise analytics report.</p>
            </div>

            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200 ${
                isDragActive
                  ? "border-primary bg-primary/5 scale-[1.02]"
                  : "border-border hover:border-primary/50 hover:bg-muted/50"
              }`}
            >
              <input {...getInputProps()} />
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                <UploadCloud className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-semibold mb-2">
                {isDragActive ? "Drop files here" : "Click or drag CSV files here"}
              </h3>
              <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                Supports multiple CSVs up to 500MB total. We'll automatically merge and clean them.
              </p>
            </div>

            {error && (
              <div className="mt-6 p-4 rounded-lg bg-destructive/10 border border-destructive/20 flex items-start gap-3 text-destructive">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <p className="text-sm font-medium">{error}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="max-w-5xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold tracking-tight">Analysis Overview</h2>
              {statusData?.status === "done" && (
                <Button onClick={handleDownload} disabled={downloading} className="shadow-lg shadow-primary/20">
                  {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
                  {downloading ? "Downloading..." : "Download PDF Report"}
                </Button>
              )}
            </div>

            <div className="p-6 rounded-xl border border-border bg-card shadow-sm">
              <div className="flex items-center gap-4">
                {statusData?.status === "processing" || statusData?.status === "pending" || uploading ? (
                  <div className="w-12 h-12 rounded-full bg-accent flex items-center justify-center text-accent-foreground">
                    <Loader2 className="w-6 h-6 animate-spin" />
                  </div>
                ) : statusData?.status === "error" ? (
                  <div className="w-12 h-12 rounded-full bg-destructive/20 flex items-center justify-center text-destructive">
                    <AlertCircle className="w-6 h-6" />
                  </div>
                ) : (
                  <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center text-green-500">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                )}
                
                <div>
                  <h3 className="font-semibold text-lg">
                    {uploading ? "Uploading files..." : 
                     statusData?.status === "pending" ? "In Queue..." :
                     statusData?.status === "processing" ? "Processing Data..." :
                     statusData?.status === "error" ? "Analysis Failed" :
                     "Analysis Complete"}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {statusData?.progress || statusData?.error_message || (statusData?.status === "done" ? "Your full EDA and forecasting report is ready." : "Please wait while we crunch the numbers.")}
                  </p>
                </div>
              </div>
            </div>

            {statusData?.status === "done" && (
               <div className="text-center p-12 border rounded-xl border-dashed bg-muted/20">
                  <h3 className="text-xl font-semibold mb-2">Report Generated Successfully</h3>
                  <p className="text-muted-foreground max-w-md mx-auto mb-6">
                    We've processed your data, generated time-series forecasts, and compiled actionable insights into a professional PDF document.
                  </p>
                  <Button onClick={handleDownload} disabled={downloading} size="lg">
                    {downloading ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : <Download className="w-5 h-5 mr-2" />}
                    {downloading ? "Downloading..." : "Download Executive Report"}
                  </Button>
               </div>
            )}

            {/* ── interactive dashboard (renders after /api/analyze returns) ── */}
            {analyzing && (
              <div className="flex items-center justify-center gap-3 py-8 text-muted-foreground">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-sm">Building interactive dashboard…</span>
              </div>
            )}
            {!analyzing && analysisResult && (
              <ResultsDashboard
                data={analysisResult}
                onExportPDF={handleDownload}
                exporting={downloading}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
