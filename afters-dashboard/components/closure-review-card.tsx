"use client";

import { useState } from "react";
import { Check, X, RefreshCcw, Pencil, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Textarea } from "./ui/textarea";
import { api } from "@/lib/api";

export interface ClosureReview {
  _id: string;
  session_id: string;
  recipient_user_id: string;
  recipient_name: string;
  draft_message: string;
  regeneration_count: number;
  status: "pending" | "approved" | "edited" | "rejected_fallback";
  final_message: string | null;
}

export function ClosureReviewCard({
  review,
  onAction,
}: {
  review: ClosureReview;
  onAction?: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [edited, setEdited] = useState(review.draft_message);

  async function approve() {
    if (busy) return;
    setBusy("approve");
    await api.approveClosure(review._id);
    setBusy(null);
    onAction?.();
  }

  async function reject() {
    if (busy) return;
    setBusy("reject");
    await api.rejectClosure(review._id);
    setBusy(null);
    onAction?.();
  }

  async function saveEdit() {
    if (busy) return;
    setBusy("edit");
    await api.editClosure(review._id, edited);
    setBusy(null);
    setEditing(false);
    onAction?.();
  }

  const pending = review.status === "pending";
  const done = !pending;

  return (
    <Card className="border-accent/30 bg-accent-soft/30">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-sm">
            Closure draft for {review.recipient_name}
          </CardTitle>
          <div className="text-xs text-ink-muted mt-0.5">
            regenerations used: {review.regeneration_count} / 1
          </div>
        </div>
        <Badge variant={pending ? "warning" : review.status === "rejected_fallback" ? "danger" : "success"}>
          {review.status.replace("_", " ")}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        {editing ? (
          <Textarea
            value={edited}
            onChange={(e) => setEdited(e.target.value)}
            rows={5}
            className="bg-white"
          />
        ) : (
          <blockquote className="text-sm leading-relaxed bg-white rounded-md border border-line p-3 whitespace-pre-wrap">
            {done && review.final_message ? review.final_message : review.draft_message}
          </blockquote>
        )}
        {pending && (
          <div className="flex items-center gap-2">
            {editing ? (
              <>
                <Button
                  variant="accent"
                  size="sm"
                  onClick={saveEdit}
                  disabled={busy != null}
                >
                  {busy === "edit" ? (
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5 mr-1.5" />
                  )}
                  approve edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setEditing(false);
                    setEdited(review.draft_message);
                  }}
                  disabled={busy != null}
                >
                  cancel
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="success"
                  size="sm"
                  onClick={approve}
                  disabled={busy != null}
                >
                  {busy === "approve" ? (
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5 mr-1.5" />
                  )}
                  approve
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditing(true)}
                  disabled={busy != null}
                >
                  <Pencil className="w-3.5 h-3.5 mr-1.5" />
                  edit
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={reject}
                  disabled={busy != null}
                >
                  {busy === "reject" ? (
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  ) : review.regeneration_count >= 1 ? (
                    <X className="w-3.5 h-3.5 mr-1.5" />
                  ) : (
                    <RefreshCcw className="w-3.5 h-3.5 mr-1.5" />
                  )}
                  {review.regeneration_count >= 1 ? "reject (use fallback)" : "reject and regenerate"}
                </Button>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
