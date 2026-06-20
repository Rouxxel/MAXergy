import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, SendHorizonal } from "lucide-react";

import { AppShell, BrandMark } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { postAdvisorChat } from "@/services/endpoints";
import type { AdvisorMessage } from "@/types";

export const Route = createFileRoute("/advisor")({
  head: () => ({ meta: [{ title: "AI advisor — Cloover" }] }),
  component: Advisor,
});

const QUICK = [
  "Explain my recommendation",
  "Why this configuration?",
  "What if I change financing term?",
];

function Advisor() {
  const [messages, setMessages] = useState<AdvisorMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! I'm your Cloover advisor. Ask me anything about your recommendation, savings, or financing options.",
      createdAt: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const send = useMutation({
    mutationFn: (text: string) =>
      postAdvisorChat({ message: text, history: messages }),
    onSuccess: (res) => {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.reply,
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
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground">
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col px-5 pt-6">
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

        <div className="-mx-1 mb-3 flex gap-2 overflow-x-auto pb-1">
          {QUICK.map((q) => (
            <button
              key={q}
              onClick={() => submit(q)}
              disabled={send.isPending}
              className="shrink-0 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground hover:border-primary/60 hover:text-foreground disabled:opacity-50"
            >
              {q}
            </button>
          ))}
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
      </div>
    </div>
  );
}

function Bubble({
  role,
  content,
  pulse,
}: {
  role: "user" | "assistant";
  content: string;
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
          "max-w-[90%] text-sm leading-relaxed text-foreground " +
          (pulse ? "animate-pulse text-muted-foreground" : "")
        }
      >
        {content}
      </div>
    </div>
  );
}