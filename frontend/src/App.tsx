import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDown,
  Bot,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  WifiOff,
  X,
} from "lucide-react";
import { fetchHealth, fetchPlanner, getErrorMessage } from "./api";
import type {
  CatalogTab,
  Course,
  CreditsFilter,
  Health,
  PlannerResponse,
} from "./types";
import { matchQuery } from "./utils";
import CalendarWeek from "./components/CalendarWeek";
import ChatAssistant from "./components/ChatAssistant";
import CourseCard from "./components/CourseCard";
import CourseModal from "./components/CourseModal";
import ScheduleSummary from "./components/ScheduleSummary";
import SelectedTray from "./components/SelectedTray";
import Toast, { type ToastData, type ToastTone } from "./components/Toast";

const TABS: { id: CatalogTab; label: string }[] = [
  { id: "all", label: "All electives" },
  { id: "compatible", label: "Compatible" },
  { id: "clashes", label: "Clashes" },
];

const CREDIT_FILTERS: { id: CreditsFilter; label: string }[] = [
  { id: "all", label: "All credits" },
  { id: "2", label: "2 credits" },
  { id: "4", label: "4 credits" },
];

const PROGRAMS = [
  "BA (Hons.) History",
  "BA (Hons.) Economics",
  "BA (Hons.) Politics",
  "BA (Hons.) Sociology",
  "BA-LLB 3rd Year",
  "BALLB4th",
  "BALLB5th",
  "LLB 2",
  "LLB 3",
  "MPP",
  "LLM General",
  "LLM Criminal",
  "LLM Commercial Law",
  "LLM Law and Tech",
  "LLM Public Law",
];

export default function App() {
  const [planner, setPlanner] = useState<PlannerResponse | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [bootError, setBootError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [tab, setTab] = useState<CatalogTab>("all");
  const [credits, setCredits] = useState<CreditsFilter>("all");
  const [query, setQuery] = useState("");
  const [modalCourseId, setModalCourseId] = useState<number | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);
  const toastCounter = useRef(0);
  const searchRef = useRef<HTMLInputElement | null>(null);
  const [program, setProgram] = useState<string>("");

  const pushToast = useCallback((message: string, tone: ToastTone = "info") => {
    toastCounter.current += 1;
    setToast({ id: toastCounter.current, message, tone });
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  const boot = useCallback(async (signal?: AbortSignal) => {
    setInitialLoading(true);
    setBootError(null);
    try {
      const [healthResult, plannerResult] = await Promise.allSettled([
        fetchHealth(signal),
        fetchPlanner([], program, signal),
      ]);
      if (signal?.aborted) {
        return;
      }
      if (healthResult.status === "fulfilled") {
        setHealth(healthResult.value);
      }
      if (plannerResult.status === "fulfilled") {
        setPlanner(plannerResult.value);
        setSelectedIds(plannerResult.value.selected.map((course) => course.id));
      } else {
        setBootError(getErrorMessage(plannerResult.reason));
      }
    } finally {
      if (!signal?.aborted) {
        setInitialLoading(false);
      }
    }
  }, [program]);

  useEffect(() => {
    const controller = new AbortController();
    void boot(controller.signal);
    return () => controller.abort();
  }, [boot]);

  const updateSelection = useCallback(
    async (
      nextIds: number[],
      notice?: { message: string; tone: ToastTone },
    ) => {
      setUpdating(true);
      try {
        const response = await fetchPlanner(nextIds, program);
        setPlanner(response);
        setSelectedIds(response.selected.map((course) => course.id));
        if (notice) {
          pushToast(notice.message, notice.tone);
        }
      } catch (error) {
        pushToast(getErrorMessage(error), "danger");
      } finally {
        setUpdating(false);
      }
    },
    [pushToast, program],
  );

  const toggleCourse = useCallback(
    (course: Course) => {
      if (!planner || updating) {
        return;
      }
      const isSelected = selectedIds.includes(course.id);
      if (isSelected) {
        void updateSelection(
          selectedIds.filter((id) => id !== course.id),
          { message: `Removed ${course.title}`, tone: "info" },
        );
        return;
      }

      if (selectedIds.length >= planner.max_electives) {
        pushToast(
          `Your plan already has ${planner.max_electives} electives. Remove one to add another.`,
          "danger",
        );
        return;
      }

      const candidate = planner.all.find((entry) => entry.id === course.id);
      if (candidate?.status === "clash") {
        const conflict = candidate.clashes[0]?.selected_course_title;
        pushToast(
          conflict
            ? `${course.title} clashes with ${conflict}.`
            : `${course.title} clashes with your current selection.`,
          "danger",
        );
        return;
      }

      void updateSelection([...selectedIds, course.id], {
        message: `Added ${course.title}`,
        tone: "success",
      });
    },
    [planner, updating, selectedIds, updateSelection, pushToast],
  );

  const removeCourse = useCallback(
    (courseId: number) => {
      if (!planner || updating) {
        return;
      }
      const course = planner.all.find((entry) => entry.id === courseId);
      void updateSelection(
        selectedIds.filter((id) => id !== courseId),
        {
          message: course ? `Removed ${course.title}` : "Elective removed",
          tone: "info",
        },
      );
    },
    [planner, updating, selectedIds, updateSelection],
  );

  const clearPlan = useCallback(() => {
    if (!planner || updating || !selectedIds.length) {
      return;
    }
    setTab("all");
    void updateSelection([], { message: "Plan cleared.", tone: "info" });
  }, [planner, updating, selectedIds, updateSelection]);

  const browseCatalogue = useCallback(() => {
    setTab("all");
    document
      .getElementById("catalogue")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => searchRef.current?.focus({ preventScroll: true }), 420);
  }, []);

  const closeModal = useCallback(() => setModalCourseId(null), []);
  const openChat = useCallback(() => setChatOpen(true), []);
  const closeChat = useCallback(() => setChatOpen(false), []);

  const visibleCourses = useMemo(() => {
    if (!planner) {
      return [];
    }
    const list = planner.all.filter((course) => {
      if (tab === "compatible" && course.status !== "compatible") {
        return false;
      }
      if (tab === "clashes" && course.status !== "clash") {
        return false;
      }
      if (credits !== "all" && course.credits !== Number(credits)) {
        return false;
      }
      return matchQuery(course, query);
    });

    if (tab === "all") {
      const order = new Map(selectedIds.map((id, index) => [id, index]));
      return list.sort((first, second) => {
        const firstIndex = order.get(first.id);
        const secondIndex = order.get(second.id);
        if (firstIndex !== undefined || secondIndex !== undefined) {
          if (firstIndex === undefined) {
            return 1;
          }
          if (secondIndex === undefined) {
            return -1;
          }
          return firstIndex - secondIndex;
        }
        return 0;
      });
    }
    return list;
  }, [planner, tab, credits, query, selectedIds]);

  const selectedCourses = planner?.selected ?? [];
  const totalCredits = planner?.summary.total_credits ?? 0;
  const maxElectives = planner?.max_electives ?? health?.max_electives ?? 4;
  const modalCourse =
    planner?.all.find((course) => course.id === modalCourseId) ?? null;
  const modalSelectedIndex = modalCourse
    ? selectedIds.indexOf(modalCourse.id)
    : -1;
  const totalCourses =
    health?.courses ?? planner?.summary.total_courses ?? 0;
  const mappedSessions = health?.mapped_sessions ?? 0;
  const trimester =
    planner?.trimester ?? health?.trimester ?? "Trimester II (AY 2026-27)";
  const connectionLabel = planner
    ? health
      ? health.llm_configured
        ? "AI assistant ready"
        : "Rules assistant"
      : "Plan synced"
    : initialLoading
      ? "Connecting"
      : "Offline";
  const connectionTone = planner
    ? "is-online"
    : initialLoading
      ? "is-connecting"
      : "is-offline";

  const emptyTitle =
    tab === "compatible" && !selectedIds.length
      ? "Pick an elective first"
      : tab === "clashes" && selectedIds.length < 2
        ? "Add a second elective"
        : query
          ? "No matching electives"
          : tab === "compatible"
            ? "No compatible electives in this filter"
            : tab === "clashes"
              ? "No clashes"
              : "Nothing to show";

  const emptyBody =
    tab === "compatible" && !selectedIds.length
      ? "Your first pick is unrestricted. Once you add it, every clash-free option appears here."
      : tab === "clashes" && selectedIds.length < 2
        ? "Clash detection starts once you have two electives in your plan."
        : query
          ? `Nothing matches \u201c${query}\u201d with the current filters.`
          : tab === "compatible"
            ? "Every remaining elective overlaps with your current plan."
            : tab === "clashes"
              ? "Your current picks do not overlap. The week is clean."
              : "Try changing the search or credit filter.";

  const resetFilters = () => {
    setQuery("");
    setCredits("all");
    setTab("all");
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="NLS Elective Planner home">
          <span className="brand-mark">NLS</span>
          <span className="brand-copy">
            <strong>Elective Planner</strong>
            <em>{trimester}</em>
          </span>
        </a>
        <div className="topbar-actions" style={{ gap: "12px", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700, color: "#000000", fontSize: "0.95rem" }}>Program:</span>
            {PROGRAMS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => {
                  if (program === p) return;
                  setProgram(p);
                  setSelectedIds([]);
                  setPlanner(null);
                  setQuery("");
                  setCredits("all");
                  setTab("all");
                }}
                style={{
                  padding: "8px 14px",
                  borderRadius: "10px",
                  border: program === p ? "2px solid #2563eb" : "2px solid #1f2937",
                  background: program === p ? "linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%)" : "linear-gradient(90deg, #111827 0%, #1f2937 100%)",
                  color: "#ffffff",
                  fontSize: "0.9rem",
                  fontWeight: 700,
                  cursor: "pointer",
                  boxShadow: program === p ? "0 4px 12px rgba(37, 99, 235, 0.4)" : "0 2px 6px rgba(0, 0, 0, 0.3)",
                  textShadow: "0 1px 2px rgba(0,0,0,0.7)",
                  letterSpacing: "0.01em",
                }}
              >
                {p}
              </button>
            ))}
            {program ? (
              <button
                type="button"
                onClick={() => {
                  setProgram("");
                  setSelectedIds([]);
                  setPlanner(null);
                  setQuery("");
                  setCredits("all");
                  setTab("all");
                }}
                style={{
                  padding: "8px 14px",
                  borderRadius: "10px",
                  border: "2px solid #dc2626",
                  background: "linear-gradient(90deg, #dc2626 0%, #b91c1c 100%)",
                  color: "#ffffff",
                  fontSize: "0.9rem",
                  fontWeight: 700,
                  cursor: "pointer",
                  boxShadow: "0 2px 6px rgba(220, 38, 38, 0.4)",
                  textShadow: "0 1px 2px rgba(0,0,0,0.7)",
                }}
              >
                Clear
              </button>
            ) : null}
          </div>
          <span className={`system-pill ${connectionTone}`}>
            <span className="system-dot" />
            {connectionLabel}
          </span>
          <button
            type="button"
            className="assistant-cta"
            onClick={openChat}
            disabled={!planner}
          >
            <Sparkles size={15} aria-hidden />
            <span>Ask Lex</span>
            <kbd>AI</kbd>
          </button>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">
              <span className="eyebrow-rule" />
              Elective planning &middot; {trimester}
            </p>
            <h1>
              Build a timetable
              <br />
              that <em>actually fits.</em>
            </h1>
            <p className="hero-lede">
              Explore every elective, map your week, and catch clashes before
              registration. Your first pick is unrestricted; add up to{" "}
              {maxElectives} and Lex can help you balance the rest.
            </p>
            <div className="hero-actions">
              <button
                type="button"
                className="primary-button"
                onClick={browseCatalogue}
                disabled={!planner}
              >
                Browse electives
                <ArrowDown size={15} aria-hidden />
              </button>
              <button
                type="button"
                className="ghost-button with-icon"
                onClick={openChat}
                disabled={!planner}
              >
                <Bot size={15} aria-hidden />
                Plan with Lex
              </button>
            </div>
          </div>

          <div className="hero-stats" aria-label="Planner statistics">
            <div className="hero-stat">
              <span>Electives mapped</span>
              <strong>{totalCourses || "\u2014"}</strong>
            </div>
            <div className="hero-stat">
              <span>Class periods</span>
              <strong>{mappedSessions || "\u2014"}</strong>
            </div>
            <div className="hero-stat">
              <span>Maximum picks</span>
              <strong>{maxElectives}</strong>
            </div>
            <p className="hero-note">
              Built from the elective list and Trimester II timetable workbook.
            </p>
          </div>
        </section>

        {!program ? (
          <section className="error-state" role="status">
            <span className="error-icon">
              <Sparkles size={22} aria-hidden />
            </span>
            <h2>Select a Program Name first</h2>
            <p>Please select a program using the buttons above to view eligible electives for that program.</p>
          </section>
        ) : initialLoading && !planner ? (
          <section className="loading-state" aria-label="Loading planner">
            <div className="loading-heading">
              <Loader2 size={18} className="spin" aria-hidden />
              <span>Loading the catalogue and timetable&hellip;</span>
            </div>
            <div className="skeleton-grid" aria-hidden="true">
              {Array.from({ length: 6 }).map((_, index) => (
                <div className="skeleton-card" key={index}>
                  <span className="skeleton-line short" />
                  <span className="skeleton-line title" />
                  <span className="skeleton-line" />
                  <span className="skeleton-line medium" />
                  <span className="skeleton-block" />
                </div>
              ))}
            </div>
          </section>
        ) : !planner ? (
          <section className="error-state" role="alert">
            <span className="error-icon">
              <WifiOff size={22} aria-hidden />
            </span>
            <h2>Could not load the planner</h2>
            <p>{bootError ?? "The API did not respond. Please try again."}</p>
            <button
              type="button"
              className="primary-button"
              onClick={() => void boot()}
            >
              <RefreshCw size={15} aria-hidden />
              Try again
            </button>
            <small>Make sure the FastAPI server is running.</small>
          </section>
        ) : (
          <>
            <SelectedTray
              selected={selectedCourses}
              max={maxElectives}
              totalCredits={totalCredits}
              updating={updating}
              onRemove={removeCourse}
              onBrowse={() => browseCatalogue()}
              onClear={clearPlan}
            />

            <div className="workspace">
              <section className="panel catalogue-panel" id="catalogue">
                <div className="panel-heading catalogue-heading">
                  <div>
                    <p className="section-kicker">Catalogue</p>
                    <h2>Choose your electives</h2>
                    <p className="panel-subcopy">
                      {planner.summary.total_courses} courses &middot;{" "}
                      {planner.summary.unscheduled_count} without a published
                      timetable
                    </p>
                  </div>
                  <span className="result-count">
                    {visibleCourses.length} shown
                  </span>
                </div>

                <div className="catalog-controls">
                  <label className="search-field">
                    <Search size={16} aria-hidden />
                    <span className="sr-only">Search electives</span>
                    <input
                      ref={searchRef}
                      id="course-search"
                      type="search"
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Search course, faculty, cohort or day"
                    />
                    {query ? (
                      <button
                        type="button"
                        className="search-clear"
                        onClick={() => setQuery("")}
                        aria-label="Clear search"
                      >
                        <X size={14} aria-hidden />
                      </button>
                    ) : null}
                  </label>

                  <div
                    className="credit-filter"
                    role="group"
                    aria-label="Filter by credits"
                  >
                    {CREDIT_FILTERS.map((filter) => (
                      <button
                        type="button"
                        key={filter.id}
                        className={credits === filter.id ? "is-active" : ""}
                        aria-pressed={credits === filter.id}
                        onClick={() => setCredits(filter.id)}
                      >
                        {filter.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="catalog-tabs">
                  {TABS.map((entry) => {
                    const count =
                      entry.id === "all"
                        ? planner.summary.total_courses
                        : entry.id === "compatible"
                          ? planner.summary.compatible_count
                          : planner.summary.clash_count;
                    return (
                      <button
                        type="button"
                        key={entry.id}
                        className={`catalog-tab ${
                          tab === entry.id ? "is-active" : ""
                        }`}
                        aria-pressed={tab === entry.id}
                        onClick={() => setTab(entry.id)}
                      >
                        {entry.label}
                        <span>{count}</span>
                      </button>
                    );
                  })}
                </div>

                {visibleCourses.length ? (
                  <div className="course-grid">
                    {visibleCourses.map((course) => (
                      <CourseCard
                        key={course.id}
                        course={course}
                        selectedIndex={
                          selectedIds.indexOf(course.id) === -1
                            ? null
                            : selectedIds.indexOf(course.id)
                        }
                        maxReached={selectedIds.length >= maxElectives}
                        updating={updating}
                        onToggle={toggleCourse}
                        onOpen={(entry) => setModalCourseId(entry.id)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="catalog-empty">
                    <span className="catalog-empty-icon">
                      <Search size={20} aria-hidden />
                    </span>
                    <h3>{emptyTitle}</h3>
                    <p>{emptyBody}</p>
                    {query || credits !== "all" || tab !== "all" ? (
                      <button
                        type="button"
                        className="small-button"
                        onClick={resetFilters}
                      >
                        Clear filters
                      </button>
                    ) : null}
                  </div>
                )}
              </section>

              <aside className="rail" aria-label="Timetable and plan insights">
                <CalendarWeek
                  selected={selectedCourses}
                  onOpenCourse={(course) => {
                    const candidate = planner.all.find(
                      (entry) => entry.id === course.id,
                    );
                    if (candidate) {
                      setModalCourseId(candidate.id);
                    }
                  }}
                  onBrowse={browseCatalogue}
                />
                <ScheduleSummary
                  selected={selectedCourses}
                  max={maxElectives}
                  onAskLex={openChat}
                />
                <div className="data-note">
                  <p className="section-kicker">Data note</p>
                  <p>
                    Courses with more than one published slot show all listed
                    times. Section allocation is handled by the academic
                    office.
                  </p>
                </div>
              </aside>
            </div>
          </>
        )}

        <footer className="site-footer">
          <p>
            NLS Elective Planner &middot; {trimester}. For planning only.
            Confirm registrations and section allocations with the academic
            office.
          </p>
          <span>Built from the official elective list and timetable workbook.</span>
        </footer>
      </main>

      <CourseModal
        course={modalCourse}
        selectedIndex={modalSelectedIndex === -1 ? null : modalSelectedIndex}
        maxReached={selectedIds.length >= maxElectives}
        updating={updating}
        onClose={closeModal}
        onToggle={toggleCourse}
      />

      <ChatAssistant
        open={chatOpen}
        onClose={closeChat}
        selectedIds={selectedIds}
        selectedCount={selectedIds.length}
        health={health}
      />

      <Toast toast={toast} onDismiss={dismissToast} />
    </div>
  );
}
