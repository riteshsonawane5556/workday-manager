import { CalendarDays } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { CalendarActionResult } from "@/types/api";

interface Props {
  result: CalendarActionResult;
}

export function CalendarActionCard({ result }: Props) {
  const badge = result.awaiting_user
    ? { variant: "warning" as const, label: "Awaiting your reply" }
    : result.executed
    ? { variant: "success" as const, label: "Executed" }
    : { variant: "info" as const, label: "Read-only" };

  return (
    <Card className="mt-2 w-full max-w-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <CalendarDays className="h-4 w-4" />
          Calendar
          <Badge variant={badge.variant} className="ml-auto">
            {badge.label}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <p className="text-sm whitespace-pre-wrap">{result.description}</p>
        {result.awaiting_user && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Reply in the chat to confirm this action.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
