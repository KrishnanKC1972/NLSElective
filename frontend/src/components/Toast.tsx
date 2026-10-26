import { useEffect } from "react";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

export type ToastTone = "success" | "danger" | "info";

export interface ToastData {
  id: number;
  message: string;
  tone: ToastTone;
}

interface Props {
  toast: ToastData | null;
  onDismiss: () => void;
}

export default function Toast({ toast, onDismiss }: Props) {
  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(onDismiss, 4200);
    return () => window.clearTimeout(timer);
  }, [toast, onDismiss]);

  if (!toast) {
    return null;
  }

  const Icon =
    toast.tone === "success"
      ? CheckCircle2
      : toast.tone === "danger"
        ? AlertTriangle
        : Info;

  return (
    <div
      className={`toast toast-${toast.tone}`}
      role={toast.tone === "danger" ? "alert" : "status"}
      aria-live="polite"
    >
      <span className="toast-icon">
        <Icon size={17} aria-hidden />
      </span>
      <p>{toast.message}</p>
      <button
        type="button"
        className="toast-close"
        onClick={onDismiss}
        aria-label="Dismiss notification"
      >
        <X size={14} aria-hidden />
      </button>
    </div>
  );
}
