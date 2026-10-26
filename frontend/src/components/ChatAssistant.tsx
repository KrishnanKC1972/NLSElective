import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Bot,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";
import { getErrorMessage, sendChat } from "../api";
import type { ChatTurn, Health } from "../types";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  provider?: "gemini" | "fallback";
  pending?: boolean;
  error?: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
  selectedIds: number[];
  selectedCount: number;
  health: Health | null;
}

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function greeting(selectedCount: number): string {
  if (!selectedCount) {
    return "Hi, I'm Lex. I can explore the elective catalogue with you, explain clashes, and read the weekly timetable. You haven't picked an elective yet \u2014 your first choice is completely unrestricted. What are you interested in?";
  }
  return "Hi, I'm Lex. I can see your current selection. Ask me to find compatible courses, explain what clashes, or summarise your week.";
}

export default function ChatAssistant({
  open,
  onClose,
  selectedIds,
  selectedCount,
  health,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const greetedRef = useRef(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (!greetedRef.current) {
      greetedRef.current = true;
      setMessages([
        {
          id: makeId(),
          role: "assistant",
          content: greeting(selectedCount),
        },
      ]);
    }
    const timer = window.setTimeout(() => inputRef.current?.focus(), 220);
    return () => window.clearTimeout(timer);
  }, [open, selectedCount]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, open]);

  const suggestions = useMemo(() => {
    if (selectedCount === 0) {
      return [
        "Which 4-credit electives meet on Saturdays?",
        "What should I consider when picking my first elective?",
        "Show me clinical electives.",
      ];
    }
    if (selectedCount >= 4) {
      return [
        "Review my final selection.",
        "Summarise my weekly calendar.",
        "Which day is my heaviest?",
      ];
    }
    const prompts = [
      "Which courses are compatible with my selection?",
      "What clashes with my selection?",
      "Summarise my weekly calendar.",
    ];
    if (selectedCount < 4) {
      prompts.push("Suggest the best next elective.");
    }
    return prompts;
  }, [selectedCount]);

  const resetChat = () => {
    setMessages([
      {
        id: makeId(),
        role: "assistant",
        content: greeting(selectedCount),
      },
    ]);
    setInput("");
    setSending(false);
    window.setTimeout(() => inputRef.current?.focus(), 50);
  };

  const sendMessage = async (raw: string) => {
    const text = raw.trim();
    if (!text || sending) {
      return;
    }

    const history: ChatTurn[] = messages
      .filter((message) => !message.pending && !message.error)
      .map((message) => ({ role: message.role, content: message.content }))
      .slice(-10);

    const userMessage: Message = {
      id: makeId(),
      role: "user",
      content: text,
    };
    const pendingId = makeId();
    const pendingMessage: Message = {
      id: pendingId,
      role: "assistant",
      content: "",
      pending: true,
    };

    setMessages((current) => [...current, userMessage, pendingMessage]);
    setInput("");
    setSending(true);

    try {
      const response = await sendChat(text, selectedIds, history);
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingId
            ? {
                ...message,
                content: response.answer,
                provider: response.provider,
                pending: false,
              }
            : message,
        ),
      );
    } catch (error) {
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingId
            ? {
                ...message,
                content: getErrorMessage(error),
                pending: false,
                error: true,
              }
            : message,
        ),
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <div
        className={`chat-backdrop ${open ? "is-open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`chat-drawer ${open ? "is-open" : ""}`}
        aria-label="Lex elective assistant"
        aria-hidden={!open}
      >
        <header className="chat-header">
          <div className="chat-brand">
            <span className="chat-avatar">
              <Bot size={19} aria-hidden />
            </span>
            <div>
              <h2>Lex</h2>
              <p>
                <span
                  className={`chat-status-dot ${
                    health?.llm_configured ? "is-online" : "is-fallback"
                  }`}
                />
                {health?.llm_configured
                  ? `AI planning assistant \u00b7 ${health.llm_model}`
                  : "Rules-based planning assistant"}
              </p>
            </div>
          </div>
          <div className="chat-header-actions">
            <button
              type="button"
              className="icon-button"
              onClick={resetChat}
              aria-label="Clear conversation"
              title="Clear conversation"
            >
              <RotateCcw size={16} aria-hidden />
            </button>
            <button
              type="button"
              className="icon-button"
              onClick={onClose}
              aria-label="Close assistant"
            >
              <X size={18} aria-hidden />
            </button>
          </div>
        </header>

        <div className="chat-context">
          <Sparkles size={13} aria-hidden />
          <span>
            Context: {selectedCount} of {health?.max_electives ?? 4} electives
            selected
          </span>
          <span className="chat-context-note">Catalogue + timetable only</span>
        </div>

        <div className="chat-messages">
          {messages.map((message) => (
            <div
              className={`chat-message from-${message.role} ${
                message.error ? "is-error" : ""
              }`}
              key={message.id}
            >
              <span className="chat-message-avatar">
                {message.role === "assistant" ? (
                  <Bot size={14} aria-hidden />
                ) : (
                  <UserRound size={14} aria-hidden />
                )}
              </span>
              <div className="chat-bubble">
                {message.pending ? (
                  <span className="typing-dots" aria-label="Lex is typing">
                    <span />
                    <span />
                    <span />
                  </span>
                ) : message.role === "assistant" ? (
                  <div className="chat-markdown">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="chat-plain">{message.content}</p>
                )}
                {message.provider ? (
                  <span className={`provider-tag provider-${message.provider}`}>
                    {message.provider === "gemini" ? "Gemini" : "Rules"}
                  </span>
                ) : null}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="chat-suggestions">
          {suggestions.map((suggestion) => (
            <button
              type="button"
              key={suggestion}
              onClick={() => void sendMessage(suggestion)}
              disabled={sending}
            >
              {suggestion}
            </button>
          ))}
        </div>

        <div className="chat-composer">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void sendMessage(input);
              }
            }}
            placeholder="Ask about clashes, compatible courses, or your week..."
            rows={2}
            maxLength={2000}
          />
          <button
            type="button"
            className="chat-send"
            onClick={() => void sendMessage(input)}
            disabled={sending || !input.trim()}
            aria-label="Send message"
          >
            {sending ? (
              <Loader2 size={17} className="spin" aria-hidden />
            ) : (
              <Send size={17} aria-hidden />
            )}
          </button>
        </div>
        <p className="chat-disclaimer">
          Lex reads the mapped Excel data. Always confirm elective choices with
          the academic office.
        </p>
      </aside>
    </>
  );
}
