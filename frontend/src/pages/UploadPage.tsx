import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, Upload, X, AlertCircle, Stethoscope, LogOut, History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { extractNameboard } from "@/lib/api";
import { signOut } from "@/lib/supabase";
import type { Session } from "@supabase/supabase-js";

interface UploadPageProps {
  session: Session | null;
}

export default function UploadPage({ session }: UploadPageProps) {
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const addFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const valid = Array.from(newFiles).filter(
      (f) => f.type === "image/jpeg" || f.type === "image/png"
    );
    const combined = [...files, ...valid].slice(0, 5);
    setFiles(combined);
    setPreviews(combined.map((f) => URL.createObjectURL(f)));
  };

  const removeFile = (index: number) => {
    const next = files.filter((_, i) => i !== index);
    setFiles(next);
    setPreviews(next.map((f) => URL.createObjectURL(f)));
  };

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      addFiles(e.dataTransfer.files);
    },
    [files]
  );

  const handleSubmit = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const result = await extractNameboard(files);
      navigate(`/review/${result.id}`, { state: { extraction: result } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Stethoscope className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-gray-900">Nameboard Extractor</span>
        </div>
        <div className="flex items-center gap-2">
          {session && (
            <Button variant="ghost" size="sm" onClick={() => navigate("/history")}>
              <History className="w-4 h-4 mr-1" />
              History
            </Button>
          )}
          {session ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">{session.user.email}</span>
              <Button variant="ghost" size="sm" onClick={() => signOut()}>
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <Button variant="outline" size="sm" onClick={() => navigate("/login")}>
              Sign in
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-10 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-gray-900">Upload Nameboard Photos</h1>
          <p className="text-muted-foreground">
            Upload 1–5 photos of the doctor's nameboard for best results
          </p>
        </div>

        {/* Tips */}
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-4 pb-4">
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Take 2–3 photos from slightly different angles</li>
              <li>• Ensure the text is clearly visible and well-lit</li>
              <li>• Include the full nameboard in the frame</li>
              <li>• JPEG or PNG only, max 10 MB per image</li>
            </ul>
          </CardContent>
        </Card>

        {/* Drop zone */}
        <Card>
          <CardContent className="pt-6">
            <div
              onDrop={onDrop}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragOver ? "border-primary bg-primary/5" : "border-gray-300 hover:border-gray-400"
              }`}
            >
              <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-700 mb-1">
                Drag photos here, or choose an option below
              </p>
              <p className="text-xs text-muted-foreground mb-4">
                {files.length}/5 images selected
              </p>
              <div className="flex gap-3 justify-center flex-wrap">
                <label>
                  <Button variant="outline" size="sm" asChild>
                    <span className="cursor-pointer">
                      <Upload className="w-4 h-4 mr-1" />
                      Browse files
                    </span>
                  </Button>
                  <input
                    type="file"
                    accept="image/jpeg,image/png"
                    multiple
                    className="hidden"
                    onChange={(e) => addFiles(e.target.files)}
                  />
                </label>
                <label>
                  <Button variant="outline" size="sm" asChild>
                    <span className="cursor-pointer">
                      <Camera className="w-4 h-4 mr-1" />
                      Take photo
                    </span>
                  </Button>
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => addFiles(e.target.files)}
                  />
                </label>
              </div>
            </div>

            {/* Thumbnails */}
            {previews.length > 0 && (
              <div className="mt-4 grid grid-cols-3 gap-3">
                {previews.map((src, i) => (
                  <div key={i} className="relative group">
                    <img
                      src={src}
                      alt={`Preview ${i + 1}`}
                      className="w-full h-24 object-cover rounded-md border"
                    />
                    <button
                      onClick={() => removeFile(i)}
                      className="absolute top-1 right-1 bg-black/60 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button
          onClick={handleSubmit}
          disabled={files.length === 0 || loading}
          className="w-full"
          size="lg"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Analyzing nameboard...
            </span>
          ) : (
            `Extract Doctor Details${files.length > 0 ? ` (${files.length} image${files.length > 1 ? "s" : ""})` : ""}`
          )}
        </Button>
      </main>
    </div>
  );
}
