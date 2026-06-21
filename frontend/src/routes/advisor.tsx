import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, SendHorizonal } from "lucide-react";

import { AppShell, BrandMark } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { postAdvisorChat } from "@/services/endpoints";
import { useResultsStore } from "@/stores/resultsStore";
import { useAssessmentStore } from "@/stores/assessmentStore";

export const Route = createFileRoute("/advisor")({
  head: () => ({ meta: [{ title: "AI advisor — MAXergy" }] }),
  component: Advisor,
});

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  suggestions?: string[];
  createdAt: number;
}

function Advisor() {
  const { forecast } = useResultsStore();
  const { submittedId } = useAssessmentStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! I'm your MAXergy advisor. Ask me anything about your recommendation, savings, or financing options.",
      createdAt: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const send = useMutation({
    mutationFn: (text: string) =>
      postAdvisorChat({
        user_message: text,
        forecast_result: forecast || null,
        assessment_id: submittedId || "",
      }),
    onSuccess: (res) => {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.advisor_message,
          suggestions: res.suggestions,
          createdAt: Date.now(),
        },
      ]);
    },
    onError: (error) => {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Sorry, I couldn't process your request. Please try again.",
          createdAt: Date.now(),
        },
      ]);
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, send.isPending]);

  const submit = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || send.isPending) return;
    setMessages((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        createdAt: Date.now(),
      },
    ]);
    setInput("");
    send.mutate(trimmed);
  };

  return (
    <AppShell>
      <header className="mb-4 flex items-center justify-between">
        <Link
          to="/results"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>
        <BrandMark />
      </header>

      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto pb-4"
      >
        {messages.map((m) => (
          <Bubble key={m.id} role={m.role} content={m.content} />
        ))}
        {send.isPending ? <Bubble role="assistant" content="…" pulse /> : null}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
        className="sticky bottom-0 mb-4 flex items-center gap-2 rounded-2xl border border-border bg-card p-2"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your savings…"
          className="h-10 border-0 bg-transparent focus-visible:ring-0"
        />
        <Button
          type="submit"
          size="icon"
          disabled={!input.trim() || send.isPending}
          className="h-10 w-10 shrink-0 bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <SendHorizonal className="h-4 w-4" />
        </Button>
      </form>
    </AppShell>
  );
}

function Bubble({
  role,
  content,
  suggestions,
  pulse,
}: {
  role: "user" | "assistant";
  content: string;
  suggestions?: string[];
  pulse?: boolean;
}) {
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground">
          {content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-2">
        <div
          className={
            "text-sm leading-relaxed text-foreground " +
            (pulse ? "animate-pulse text-muted-foreground" : "")
          }
        >
          {content}
        </div>
        {suggestions && suggestions.length > 0 && (
          <div className="space-y-1">
            {suggestions.map((s, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-primary" />
                <span>{s}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}