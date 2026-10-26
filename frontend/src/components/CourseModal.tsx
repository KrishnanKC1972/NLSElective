import { useEffect } from "react";
import type { CSSProperties } from "react";
import {
  AlertTriangle,
  CalendarClock,
  Check,
  Info,
  MapPin,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import type { Candidate } from "../types";
import {
  courseColor,
  formatCredits,
  formatMinutes,
  statusMeta,
} from "../utils";

interface Props {
  course: Candidate | null;
  selectedIndex: number | null;
  maxReached: boolean;
  updating: boolean;
  onClose: () => void;
  onToggle: (course: Candidate) => void;
}

export default function CourseModal({
  course,
  selectedIndex,
  maxReached,
  updating,
  onClose,
  onToggle,
}: Props) {
  useEffect(() => {
    if (!course) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [course, onClose]);

  if (!course) {
    return null;
  }

  const meta = statusMeta(course.status);
  const color = selectedIndex === null ? null : courseColor(selectedIndex);
  const style = color
    ? ({
        "--course-bg": color.bg,
        "--course-border": color.border,
        "--course-ink": color.ink,
        "--course-solid": color.solid,
      } as CSSProperties)
    : undefined;
  const isSelected = course.status === "selected";
  const disabled =
    updating ||
    (!isSelected && (course.status === "clash" || maxReached));
  const uniqueClashes = Array.from(
    new Map(
      course.clashes.map((clash) => [
        `${clash.selected_course_id}-${clash.day}-${clash.overlap_start}-${clash.overlap_end}`,
        clash,
      ]),
    ).values(),
  );
  const buttonLabel = isSelected
    ? "Remove from plan"
    : course.status === "clash"
      ? "Cannot add \u2014 timetable clash"
      : maxReached
        ? "Plan is full"
        : course.status === "unscheduled"
          ? "Add anyway"
          : "Add to plan";

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="course-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="course-modal-title"
        style={style}
      >
        <div className="modal-topbar">
          <span className={`status-pill tone-${meta.tone}`}>{meta.label}</span>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close course details"
            autoFocus
          >
            <X size={18} aria-hidden />
          </button>
        </div>

        <div className="modal-title-block">
          <p className="modal-credits">
            {formatCredits(course.credits)}
            {course.concentration ? (
              <span className="modal-concentration">
                <Sparkles size={12} aria-hidden />
                {course.concentration}
              </span>
            ) : null}
          </p>
          <h2 id="course-modal-title">{course.title}</h2>
          <p className="modal-faculty">{course.faculty}</p>
          <div className="course-chips">
            {course.clinical ? <span className="chip">Clinical</span> : null}
            {course.survey_elective ? <span className="chip">Survey</span> : null}
            {course.ba_practice ? (
              <span className="chip">BA practice</span>
            ) : null}
            {course.audience.length ? (
              <span className="chip">
                <Users size={11} aria-hidden />
                {course.audience.length} cohorts
              </span>
            ) : null}
          </div>
        </div>

        {course.status === "clash" && uniqueClashes.length ? (
          <div className="modal-alert">
            <div className="modal-alert-title">
              <AlertTriangle size={16} aria-hidden />
              Timetable clash
            </div>
            <ul>
              {uniqueClashes.map((clash) => (
                <li key={`${clash.selected_course_id}-${clash.day}-${clash.overlap_start}`}>
                  <strong>{clash.selected_course_title}</strong>
                  <span>
                    {clash.day} &middot; overlaps {clash.overlap_label}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {course.status === "compatible" ? (
          <div className="modal-ok">
            <Check size={15} aria-hidden />
            Clash-free with your current selection.
          </div>
        ) : null}

        <section className="modal-section">
          <h3>
            <CalendarClock size={15} aria-hidden />
            Published timetable
          </h3>
          {course.blocks.length ? (
            <div className="modal-schedule">
              {course.blocks.map((block) => (
                <div className="modal-schedule-row" key={`${block.day}-${block.start_min}`}>
                  <span className="modal-day">{block.day}</span>
                  <div>
                    <strong>{block.time_label}</strong>
                    <span>
                      {block.duration_label} &middot;{" "}
                      {block.classrooms.length
                        ? block.classrooms.join(" / ")
                        : "Room TBA"}
                    </span>
                    {block.segments.length > 1 ? (
                      <em>
                        {block.segments
                          .map((segment) => segment.time_label)
                          .join(" \u00b7 ")}
                      </em>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="modal-empty">
              <Info size={14} aria-hidden />
              No timetable was published for this elective. It will not block
              other slots in the planner.
            </p>
          )}
          <p className="modal-contact">
            {formatMinutes(course.weekly_minutes)} contact time / week
          </p>
        </section>

        {course.audience.length ? (
          <section className="modal-section">
            <h3>
              <Users size={15} aria-hidden />
              Open to
            </h3>
            <div className="audience-chips">
              {course.audience.map((group) => (
                <span className="chip" key={group}>
                  {group}
                </span>
              ))}
            </div>
          </section>
        ) : null}

        {course.timetable_names.length ? (
          <section className="modal-section modal-source">
            <h3>
              <MapPin size={15} aria-hidden />
              Timetable listing
            </h3>
            <p>{course.timetable_names.join(" \u00b7 ")}</p>
          </section>
        ) : null}

        <div className="modal-actions">
          <button type="button" className="ghost-button" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className={`add-button large ${isSelected ? "is-selected" : ""}`}
            disabled={disabled}
            onClick={() => onToggle(course)}
          >
            {isSelected ? <X size={15} aria-hidden /> : <Check size={15} aria-hidden />}
            {buttonLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
