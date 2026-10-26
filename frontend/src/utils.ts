import type { Candidate, Course, CourseStatus } from "./types";

export interface CourseColor {
  name: string;
  bg: string;
  border: string;
  ink: string;
  solid: string;
}

export const COURSE_COLORS: CourseColor[] = [
  {
    name: "blue",
    bg: "#e7effa",
    border: "#3569a8",
    ink: "#1e3f66",
    solid: "#3569a8",
  },
  {
    name: "teal",
    bg: "#e2f3ee",
    border: "#2f7d6a",
    ink: "#1a4e43",
    solid: "#2f7d6a",
  },
  {
    name: "amber",
    bg: "#faefda",
    border: "#b97a20",
    ink: "#6f470f",
    solid: "#b97a20",
  },
  {
    name: "rose",
    bg: "#f9e7eb",
    border: "#ad4a60",
    ink: "#722a3a",
    solid: "#ad4a60",
  },
  {
    name: "violet",
    bg: "#f0eaf9",
    border: "#7050a8",
    ink: "#48326f",
    solid: "#7050a8",
  },
  {
    name: "olive",
    bg: "#eef3e1",
    border: "#6b8435",
    ink: "#41501c",
    solid: "#6b8435",
  },
  {
    name: "coral",
    bg: "#fbeae1",
    border: "#bf6438",
    ink: "#77391b",
    solid: "#bf6438",
  },
  {
    name: "slate",
    bg: "#eaeef2",
    border: "#536677",
    ink: "#303d48",
    solid: "#536677",
  },
];

export const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

export const DAY_SHORT: Record<string, string> = {
  Monday: "Mon",
  Tuesday: "Tue",
  Wednesday: "Wed",
  Thursday: "Thu",
  Friday: "Fri",
  Saturday: "Sat",
  Sunday: "Sun",
};

export function courseColor(index: number): CourseColor {
  return COURSE_COLORS[index % COURSE_COLORS.length];
}

export function formatCredits(credits: number): string {
  const value = Number.isInteger(credits) ? credits : credits.toFixed(1);
  return `${value} ${credits === 1 ? "credit" : "credits"}`;
}

export function formatCreditsShort(credits: number): string {
  return Number.isInteger(credits) ? `${credits}` : credits.toFixed(1);
}

export function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) {
    return `${rest}m`;
  }
  return rest ? `${hours}h ${rest}m` : `${hours}h`;
}

export interface StatusMeta {
  label: string;
  tone: "accent" | "success" | "danger" | "neutral" | "muted";
}

export function statusMeta(status: CourseStatus): StatusMeta {
  switch (status) {
    case "selected":
      return { label: "Selected", tone: "accent" };
    case "compatible":
      return { label: "Compatible", tone: "success" };
    case "clash":
      return { label: "Clash", tone: "danger" };
    case "unscheduled":
      return { label: "No timetable", tone: "muted" };
    default:
      return { label: "First pick", tone: "neutral" };
  }
}

export function matchQuery(course: Course, query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return true;
  }
  const haystack = [
    course.title,
    course.faculty,
    course.concentration ?? "",
    course.schedule_label,
    ...course.audience,
  ]
    .join(" ")
    .toLowerCase();
  return normalized
    .split(/\s+/)
    .filter(Boolean)
    .every((token) => haystack.includes(token));
}

export function clashSummary(course: Candidate): string {
  if (!course.clashes.length) {
    return "";
  }
  const conflicts = Array.from(
    new Set(course.clashes.map((clash) => clash.selected_course_title)),
  );
  const first = course.clashes[0];
  return `${conflicts.length} selected course${
    conflicts.length === 1 ? "" : "s"
  } \u00b7 ${first.day} ${first.overlap_label}`;
}

export function schedulePreview(course: Course, limit = 2) {
  return course.blocks.slice(0, limit).map((block) => ({
    day: DAY_SHORT[block.day] ?? block.day,
    time: block.time_label,
  }));
}

export function uniqueDays(course: Course): string[] {
  return Array.from(new Set(course.blocks.map((block) => block.day)));
}

export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || target.isContentEditable;
}
