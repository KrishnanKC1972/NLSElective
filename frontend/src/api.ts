import type {
  ChatResponse,
  ChatTurn,
  ClashInfo,
  Course,
  Health,
  PlannerResponse,
} from "./types";

const API_BASE = (
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api"
).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  clashes: ClashInfo[];

  constructor(message: string, status: number, clashes: ClashInfo[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.clashes = clashes;
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  let clashes: ClashInfo[] = [];
  try {
    const payload = (await response.json()) as {
      detail?: string | { message?: string; clashes?: ClashInfo[] };
    };
    if (typeof payload.detail === "string") {
      message = payload.detail;
    } else if (payload.detail && typeof payload.detail === "object") {
      message = payload.detail.message ?? message;
      clashes = payload.detail.clashes ?? [];
    }
  } catch {
    // Keep the generic message if the server did not return JSON.
  }
  return new ApiError(message, response.status, clashes);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });
  if (!response.ok) {
    throw await toApiError(response);
  }
  return (await response.json()) as T;
}

export function fetchPlanner(
  selectedIds: number[],
  program?: string | null,
  signal?: AbortSignal,
): Promise<PlannerResponse> {
  const payload: { selected_ids: number[]; program?: string | null } = {
    selected_ids: selectedIds,
  };
  if (program && program.trim()) {
    payload.program = program.trim();
  }
  return request<PlannerResponse>("/plans/recommendations", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function fetchCourses(program?: string | null, signal?: AbortSignal): Promise<Course[]> {
  const query = program && program.trim() ? `?program=${encodeURIComponent(program.trim())}` : "";
  return request<Course[]>(`/courses${query}`, { signal });
}

export function fetchHealth(signal?: AbortSignal): Promise<Health> {
  return request<Health>("/health", { signal });
}

export function sendChat(
  message: string,
  selectedIds: number[],
  history: ChatTurn[],
  signal?: AbortSignal,
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      selected_ids: selectedIds,
      history,
    }),
    signal,
  });
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}
