import { Mail } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ProcessingResult } from "@/types/api";

interface Props {
  result: ProcessingResult;
}

export function EmailTriageCard({ result }: Props) {
  return (
    <Card className="mt-2 w-full max-w-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Mail className="h-4 w-4" />
          Email Triage
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <div className="flex gap-2">
          <Badge variant="muted">{result.processed} processed</Badge>
          <Badge variant={result.actionable > 0 ? "warning" : "success"}>
            {result.actionable} actionable
          </Badge>
        </div>
        {result.actionable > 0 && (
          <p className="text-xs text-muted-foreground">
            Drafts ready — check the Pending Approvals panel →
          </p>
        )}
      </CardContent>
    </Card>
  );
}
