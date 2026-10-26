export interface Session {
  day: string;
  day_index: number;
  start_min: number;
  end_min: number;
  start_label: string;
  end_label: string;
  time_label: string;
  duration_min: number;
  duration_label: string;
  classrooms: string[];
  faculties: string[];
}

export interface Block {
  day: string;
  day_index: number;
  start_min: number;
  end_min: number;
  start_label: string;
  end_label: string;
  time_label: string;
  duration_min: number;
  duration_label: string;
  classrooms: string[];
  faculties: string[];
  segments: Session[];
}

export interface Course {
  id: number;
  title: string;
  faculty: string;
  credits: number;
  concentration: string | null;
  survey_elective: boolean;
  ba_practice: boolean;
  clinical: boolean;
  eligibility: Record<string, boolean>;
  audience: string[];
  timetable_names: string[];
  sessions: Session[];
  blocks: Block[];
  schedule_label: string;
  has_schedule: boolean;
  session_count: number;
  day_count: number;
  weekly_minutes: number;
}

export type CourseStatus =
  | "selected"
  | "available"
  | "compatible"
  | "clash"
  | "unscheduled";

export interface ClashInfo {
  selected_course_id: number;
  selected_course_title: string;
  day: string;
  day_index: number;
  overlap_start: number;
  overlap_end: number;
  overlap_label: string;
}

export interface Candidate extends Course {
  status: CourseStatus;
  clash_count: number;
  clashes: ClashInfo[];
}

export interface PlanSummary {
  total_courses: number;
  selected_count: number;
  clash_count: number;
  compatible_count: number;
  unscheduled_count: number;
  remaining_slots: number;
  total_credits: number;
  max_electives: number;
}

export interface PlannerResponse {
  selected: Course[];
  all: Candidate[];
  clash_ids: number[];
  compatible_ids: number[];
  unscheduled_ids: number[];
  can_select_more: boolean;
  max_electives: number;
  summary: PlanSummary;
  trimester: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  provider: "gemini" | "fallback";
  model: string | null;
}

export interface Health {
  status: string;
  database: string;
  courses: number;
  sessions: number;
  mapped_sessions: number;
  unmapped_sessions: number;
  llm_configured: boolean;
  llm_model: string;
  trimester: string;
  max_electives: number;
}

export type CatalogTab = "all" | "compatible" | "clashes";
export type CreditsFilter = "all" | "2" | "4";
