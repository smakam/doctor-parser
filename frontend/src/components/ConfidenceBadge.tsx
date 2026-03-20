import { Badge } from "@/components/ui/badge";

interface ConfidenceBadgeProps {
  confidence: number;
  showValue?: boolean;
}

export function ConfidenceBadge({ confidence, showValue = false }: ConfidenceBadgeProps) {
  if (confidence >= 0.85) {
    return (
      <Badge variant="success">
        {showValue ? `${Math.round(confidence * 100)}%` : "High"}
      </Badge>
    );
  }
  if (confidence >= 0.70) {
    return (
      <Badge variant="warning">
        {showValue ? `${Math.round(confidence * 100)}%` : "Medium"}
      </Badge>
    );
  }
  return (
    <Badge variant="danger">
      {showValue ? `${Math.round(confidence * 100)}%` : "Low — check manually"}
    </Badge>
  );
}
