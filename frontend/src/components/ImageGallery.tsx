import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type { ImageQualityResult } from "@/types/nameboard";

interface ImageGalleryProps {
  images: ImageQualityResult[];
}

export function ImageGallery({ images }: ImageGalleryProps) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
        Uploaded Images
      </h3>
      {images.map((img, i) => (
        <div key={i} className="space-y-2">
          <div className="relative rounded-lg overflow-hidden border">
            <img
              src={img.imagekit_url}
              alt={`Nameboard ${i + 1}`}
              className="w-full object-cover max-h-52"
            />
            <div className="absolute top-2 right-2">
              <Badge variant={img.quality === "GOOD" ? "success" : "danger"}>
                {img.quality === "GOOD" ? "Good quality" : "Poor quality"}
              </Badge>
            </div>
          </div>

          {img.warnings.map((warning, j) => (
            <Alert key={j} variant="warning" className="py-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-xs">{warning}</AlertDescription>
            </Alert>
          ))}

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>OCR confidence: {Math.round(img.average_word_confidence * 100)}%</span>
            {img.detected_languages.length > 0 && (
              <span>· Languages: {img.detected_languages.join(", ")}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
