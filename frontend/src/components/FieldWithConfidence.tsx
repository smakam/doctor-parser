import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { cn } from "@/lib/utils";
import type { ExtractedField } from "@/types/nameboard";

interface FieldWithConfidenceProps {
  label: string;
  field: ExtractedField | null;
  fieldKey: string;
  value: string;
  onChange: (key: string, value: string) => void;
  multiline?: boolean;
}

export function FieldWithConfidence({
  label,
  field,
  fieldKey,
  value,
  onChange,
  multiline = false,
}: FieldWithConfidenceProps) {
  const confidence = field?.confidence ?? 0;
  const isLow = confidence < 0.70 && value;
  const isMedium = confidence >= 0.70 && confidence < 0.85 && value;

  const borderClass = cn(
    isLow && "border-red-300 focus-visible:ring-red-400",
    isMedium && "border-amber-300 focus-visible:ring-amber-400"
  );

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label htmlFor={fieldKey}>{label}</Label>
        {field && value && <ConfidenceBadge confidence={confidence} showValue />}
      </div>
      {multiline ? (
        <Textarea
          id={fieldKey}
          value={value}
          onChange={(e) => onChange(fieldKey, e.target.value)}
          className={borderClass}
          rows={3}
          placeholder={`Enter ${label.toLowerCase()}`}
        />
      ) : (
        <Input
          id={fieldKey}
          value={value}
          onChange={(e) => onChange(fieldKey, e.target.value)}
          className={borderClass}
          placeholder={`Enter ${label.toLowerCase()}`}
        />
      )}
      {isLow && (
        <p className="text-xs text-red-600">Low confidence — please verify this field</p>
      )}
    </div>
  );
}
