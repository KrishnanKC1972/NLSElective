import type { CSSProperties } from "react";
import {
  AlertTriangle,
  MapPin,
  Plus,
  Sparkles,
  X,
} from "lucide-react";
import type { Candidate } from "../types";
import {
  clashSummary,
  courseColor,
  formatCreditsShort,
  schedulePreview,
  statusMeta,
} from "../utils";

interface Props {
  course: Candidate;
  selectedIndex: number | null;
  maxReached: boolean;
  updating: boolean;
  onToggle: (course: Candidate) => void;
  onOpen: (course: Candidate) => void;
}

export default function CourseCard({
  course,
  selectedIndex,
  maxReached,
  updating,
  onToggle,
  onOpen,
}: Props) {
  const meta = statusMeta(course.status);
  const color = selectedIndex === null ? null : courseColor(selectedIndex);
  const isSelected = course.status === "selected";
  const isClash = course.status === "clash";
  const addDisabled =
    updating ||
    isClash ||
    (maxReached && !isSelected);
  const preview = schedulePreview(course);
  const style = color
    ? ({
        "--course-bg": color.bg,
        "--course-border": color.border,
        "--course-ink": color.ink,
        "--course-solid": color.solid,
      } as CSSProperties)
    : undefined;

  const buttonLabel = isSelected
    ? "Remove"
    : isClash
      ? "Clash"
      : maxReached
        ? "Limit reached"
        : course.status === "unscheduled"
          ? "Add anyway"
          : "Add elective";

  return (
    <article
      className={`course-card status-${course.status}`}
      style={style}
      aria-label={course.title}
    >
      <div className="course-card-top">
        <span className="credit-badge">
          {formatCreditsShort(course.credits)} cr
        </span>
        <span className={`status-pill tone-${meta.tone}`}>
          {isSelected && color ? (
            <span
              className="status-dot"
              style={{ background: color.solid }}
            />
          ) : null}
          {meta.label}
        </span>
      </div>

      <button
        type="button"
        className="course-title"
        onClick={() => onOpen(course)}
        title={course.faculty ? `${course.title} | ${course.faculty}` : course.title}
        style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", textAlign: "left", gap: "4px" }}
      >
        <span>{course.title}</span>
        {course.faculty ? (
          <span style={{ fontWeight: 700, color: "var(--text-strong)", fontSize: "0.95em" }}>
            {course.faculty}
          </span>
        ) : null}
      </button>
      {course.faculty ? (
        <p className="course-faculty" style={{ fontWeight: 700, color: "var(--text-strong)" }}>
          {course.faculty}
        </p>
      ) : null}

      <div className="course-chips">
        {course.concentration ? (
          <span className="chip chip-concentration">
            <Sparkles size={11} aria-hidden />
            {course.concentration}
          </span>
        ) : null}
        {course.clinical ? <span className="chip">Clinical</span> : null}
        {course.survey_elective ? <span className="chip">Survey</span> : null}
        {course.ba_practice ? <span className="chip">BA practice</span> : null}
        {!course.has_schedule ? (
          <span className="chip chip-warn">Timetable TBD</span>
        ) : null}
      </div>

      <div className="schedule-mini">
        {preview.length ? (
          <>
            {preview.map((slot) => (
              <div className="schedule-line" key={`${slot.day}-${slot.time}`}>
                <span className="schedule-day">{slot.day}</span>
                <span>{slot.time}</span>
              </div>
            ))}
            {course.blocks.length > preview.length ? (
              <div className="schedule-more">
                +{course.blocks.length - preview.length} more slot
                {course.blocks.length - preview.length === 1 ? "" : "s"}
              </div>
            ) : null}
          </>
        ) : (
          <div className="schedule-line schedule-none">
            <MapPin size={13} aria-hidden />
            Timetable not published
          </div>
        )}
      </div>

      {isClash ? (
        <div className="clash-note">
          <AlertTriangle size={13} aria-hidden />
          <span>
            Clashes with {clashSummary(course)}
            {course.clashes[0] ? (
              <em>{course.clashes[0].selected_course_title}</em>
            ) : null}
          </span>
        </div>
      ) : null}

      <div className="course-actions">
        <button
          type="button"
          className="text-button"
          onClick={() => onOpen(course)}
        >
          Details
        </button>
        <button
          type="button"
          className={`add-button ${
            isSelected ? "is-selected" : isClash ? "is-clash" : ""
          }`}
          disabled={addDisabled}
          onClick={() => onToggle(course)}
          title={
            isClash
              ? "This course overlaps with a selected elective"
              : maxReached && !isSelected
                ? "Remove an elective to add another"
                : undefined
          }
        >
          {isSelected ? (
            <X size={14} aria-hidden />
          ) : isClash ? (
            <AlertTriangle size={14} aria-hidden />
          ) : (
            <Plus size={14} aria-hidden />
          )}
          {buttonLabel}
        </button>
      </div>
    </article>
  );
}
