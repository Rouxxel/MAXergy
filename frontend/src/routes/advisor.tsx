import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, SendHorizonal } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { AppShell, BrandMark } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/services/apiClient";
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
  /** The advisor computed a plan in this turn (chat onboarding). */
  planReady?: boolean;
  createdAt: number;
}

const WELCOME_WITH_PLAN =
  "Hi, I'm your MAXergy advisor. Ask me anything about your plan — why this bundle, the loan, or what changes after payoff.";
const WELCOME_WITHOUT_PLAN =
  "Hi, I'm your MAXergy advisor. You haven't completed an assessment yet — I can walk you through it here, one question at a time, or you can use the assessment form.";

function Advisor() {
  const { forecast, recommendation, setPlan } = useResultsStore();
  const { submittedId } = useAssessmentStore();
  const plan = forecast && recommendation ? { forecast, recommendation } : null;
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: plan ? WELCOME_WITH_PLAN : WELCOME_WITHOUT_PLAN,
      createdAt: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Cap client input length to match API limit
  const MAX_INPUT_LENGTH = 1000;

  const send = useMutation({
    mutationFn: ({ text, history }: { text: string; history: Message[] }) =>
      postAdvisorChat({
        user_message: text,
        plan,
        assessment_id: submittedId || null,
        conversation_history: history
          .filter((m) => m.id !== "welcome")
          .slice(-20)
          .map((m) => ({ role: m.role, content: m.content.slice(0, 4000) })),
      }),
    onSuccess: (res) => {
      // Chat onboarding finished: the plan comes from the same services as POST /plan.
      if (res.plan) setPlan(res.plan);
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.advisor_message,
          suggestions: res.suggestions,
          planReady: !!res.plan,
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
          content: advisorErrorMessage(error),
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
    send.mutate({ text: trimmed, history: messages });
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

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto pb-4">
        {messages.map((m) => (
          <div key={m.id} className="space-y-2">
            <Bubble role={m.role} content={m.content} suggestions={m.suggestions} />
            {m.planReady ? (
              <Button asChild size="sm" className="bg-primary text-primary-foreground">
                <Link to="/results">See your results</Link>
              </Button>
            ) : null}
          </div>
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

/** The backend's `detail` (e.g. "The AI advisor is busy right now…") when available. */
function advisorErrorMessage(error: unknown): string {
  const body = error instanceof ApiError ? error.body : null;
  const detail =
    body && typeof body === "object" && "detail" in body
      ? (body as { detail: unknown }).detail
      : null;
  return typeof detail === "string"
    ? `Sorry — ${detail}`
    : "Sorry, I couldn't process your request. Please try again.";
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
      <div
        className={
          "max-w-[90%] rounded-2xl rounded-bl-md px-4 py-3 text-sm leading-relaxed text-white " +
          (pulse ? "animate-pulse opacity-60" : "")
        }
        style={{ backgroundColor: "#6C63FF" }}
      >
        {pulse ? (
          <span>…</span>
        ) : (
          <ReactMarkdown
            skipHtml={true}
            disallowedElements={["script", "iframe", "object", "embed", "form", "input", "button"]}
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              strong: ({ children }) => (
                <strong className="font-semibold text-white">{children}</strong>
              ),
              em: ({ children }) => <em className="italic">{children}</em>,
              ul: ({ children }) => <ul className="mb-2 ml-4 list-disc space-y-1">{children}</ul>,
              ol: ({ children }) => (
                <ol className="mb-2 ml-4 list-decimal space-y-1">{children}</ol>
              ),
              li: ({ children }) => <li className="leading-snug">{children}</li>,
              h1: ({ children }) => <h1 className="mb-1 text-base font-bold">{children}</h1>,
              h2: ({ children }) => <h2 className="mb-1 text-sm font-bold">{children}</h2>,
              h3: ({ children }) => <h3 className="mb-1 text-sm font-semibold">{children}</h3>,
              blockquote: ({ children }) => (
                <blockquote className="my-2 border-l-2 border-white/30 pl-3 text-xs italic text-white/90">
                  {children}
                </blockquote>
              ),
              code: ({ children }) => (
                <code className="rounded bg-white/20 px-1 py-0.5 font-mono text-xs">
                  {children}
                </code>
              ),
              a: ({ children, href }) => (
                <a href={href} target="_blank" rel="noopener noreferrer" className="underline">
                  {children}
                </a>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
        {suggestions && suggestions.length > 0 && (
          <div className="mt-2 space-y-1 border-t border-white/20 pt-2">
            {suggestions.map((s, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-white/80">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-white" />
                <span>{s}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
