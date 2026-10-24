import React, { useEffect, useRef, useState } from "react";
import { ScrollView, View, Text, Pressable, KeyboardAvoidingView, Platform } from "react-native";
import { useRouter } from "expo-router";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, SendHorizonal } from "lucide-react-native";

import { Header } from "@/components/header";
import { BackButton } from "@/components/back-button";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/services/apiClient";
import { postAdvisorChat } from "@/services/endpoints";
import { useResultsStore } from "@/stores/resultsStore";
import { useAssessmentStore } from "@/stores/assessmentStore";

const randomId = () => Math.random().toString(36).substring(2, 15);

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

/** The backend's `detail` (e.g. "The AI advisor is busy right now…") when available. */
function advisorErrorMessage(error: unknown): string {
  const body = error instanceof ApiError ? error.body : null;
  const detail = body && typeof body === "object" && "detail" in body ? (body as { detail: unknown }).detail : null;
  return typeof detail === "string" ? `Sorry — ${detail}` : "Sorry, I couldn't process your request. Please try again.";
}

export default function Advisor() {
  const router = useRouter();
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
  const scrollRef = useRef<ScrollView>(null);

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
          id: randomId(),
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
          id: randomId(),
          role: "assistant",
          content: advisorErrorMessage(error),
          createdAt: Date.now(),
        },
      ]);
    },
  });

  useEffect(() => {
    // Scroll to bottom when messages update
    setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, [messages, send.isPending]);

  const submit = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || send.isPending) return;
    setMessages((m) => [
      ...m,
      {
        id: randomId(),
        role: "user",
        content: trimmed,
        createdAt: Date.now(),
      },
    ]);
    setInput("");
    send.mutate({ text: trimmed, history: messages });
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      className="flex-1 bg-background"
      keyboardVerticalOffset={Platform.OS === "ios" ? 88 : 0}
    >
      <Header />
      
      {/* Back navigation header row */}
      <View className="flex-row items-center justify-between px-5 py-2 border-b border-border bg-background">
        <BackButton label="Results" />
      </View>

      <ScrollView
        ref={scrollRef}
        className="flex-1 px-5 pt-4"
        contentContainerStyle={{ paddingBottom: 24 }}
      >
        <View className="space-y-4">
          {messages.map((m) => (
            <View key={m.id} className="space-y-2">
              <Bubble
                role={m.role}
                content={m.content}
                suggestions={m.suggestions}
                onSuggestionPress={submit}
              />
              {m.planReady ? (
                <Button onPress={() => router.push("/results")} className="bg-primary self-start px-4 h-9">
                  See your results
                </Button>
              ) : null}
            </View>
          ))}
          {send.isPending ? <Bubble role="assistant" content="…" pulse /> : null}
        </View>
      </ScrollView>

      {/* Input container bar */}
      <View className="p-3 border-t border-border bg-card flex-row items-center space-x-2">
        <Input
          value={input}
          onChangeText={setInput}
          placeholder="Ask about your savings…"
          className="flex-1 h-11 border-0 bg-transparent"
        />
        <Button
          onPress={() => submit(input)}
          disabled={!input.trim() || send.isPending}
          className="h-10 w-10 bg-primary rounded-full items-center justify-center shrink-0 ml-2"
        >
          <SendHorizonal size={18} className="text-primary-foreground" />
        </Button>
      </View>
    </KeyboardAvoidingView>
  );
}

function renderBoldText(text: string) {
  const parts = text.split("**");
  return parts.map((part, index) => {
    if (index % 2 === 1) {
      return (
        <Text key={index} className="font-bold text-white">
          {part}
        </Text>
      );
    }
    
    const codeParts = part.split("`");
    if (codeParts.length > 1) {
      return codeParts.map((subPart, subIndex) => {
        if (subIndex % 2 === 1) {
          return (
            <Text key={subIndex} className="bg-white/20 font-mono text-xs px-1 rounded">
              {subPart}
            </Text>
          );
        }
        return <Text key={subIndex}>{subPart}</Text>;
      });
    }
    
    return <Text key={index}>{part}</Text>;
  });
}

function MarkdownText({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <View className="space-y-1">
      {lines.map((line, idx) => {
        if (line.startsWith("### ")) {
          return (
            <Text key={idx} className="font-bold text-white text-base mt-2 mb-1">
              {line.slice(4)}
            </Text>
          );
        }
        if (line.startsWith("## ")) {
          return (
            <Text key={idx} className="font-bold text-white text-base mt-2 mb-1">
              {line.slice(3)}
            </Text>
          );
        }
        if (line.startsWith("# ")) {
          return (
            <Text key={idx} className="font-bold text-white text-lg mt-2 mb-1">
              {line.slice(2)}
            </Text>
          );
        }

        if (line.startsWith("- ") || line.startsWith("* ")) {
          const content = line.slice(2);
          return (
            <View key={idx} className="flex-row items-start pl-2 py-0.5 mt-0.5">
              <Text className="text-white text-sm">•</Text>
              <Text className="text-white text-sm ml-2 flex-1">{renderBoldText(content)}</Text>
            </View>
          );
        }

        if (line.startsWith("> ")) {
          return (
            <View key={idx} className="border-l-2 border-white/30 pl-3 py-1 my-1">
              <Text className="text-white/80 text-xs italic">{renderBoldText(line.slice(2))}</Text>
            </View>
          );
        }

        if (!line.trim()) {
          return <View key={idx} className="h-2" />;
        }

        return (
          <Text key={idx} className="text-white text-sm leading-relaxed mb-1">
            {renderBoldText(line)}
          </Text>
        );
      })}
    </View>
  );
}

function Bubble({
  role,
  content,
  suggestions,
  pulse,
  onSuggestionPress,
}: {
  role: "user" | "assistant";
  content: string;
  suggestions?: string[];
  pulse?: boolean;
  onSuggestionPress?: (text: string) => void;
}) {
  if (role === "user") {
    return (
      <View className="flex-row justify-end mb-2">
        <View className="max-w-[85%] rounded-2xl rounded-tr-md bg-primary px-4 py-2.5">
          <Text className="text-sm font-semibold text-primary-foreground leading-relaxed">
            {content}
          </Text>
        </View>
      </View>
    );
  }
  
  return (
    <View className="flex-row justify-start mb-2">
      <View
        className={
          "max-w-[90%] rounded-2xl rounded-bl-md px-4 py-3 bg-[#6C63FF] " +
          (pulse ? "opacity-60" : "")
        }
      >
        {pulse ? (
          <Text className="text-white font-bold">…</Text>
        ) : (
          <MarkdownText content={content} />
        )}
        
        {suggestions && suggestions.length > 0 && (
          <View className="mt-2.5 border-t border-white/20 pt-2 space-y-1.5">
            {suggestions.map((s, i) => (
              <Pressable
                key={i}
                onPress={() => onSuggestionPress?.(s)}
                className="flex-row items-center space-x-2 py-1 active:opacity-70"
              >
                <View className="h-1.5 w-1.5 rounded-full bg-white" />
                <Text className="text-xs text-white/90 underline font-medium ml-1.5 flex-1">{s}</Text>
              </Pressable>
            ))}
          </View>
        )}
      </View>
    </View>
  );
}
