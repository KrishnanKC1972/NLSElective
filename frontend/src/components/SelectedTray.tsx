import type { CSSProperties } from "react";
import { Loader2, Plus, Trash2 } from "lucide-react";
import type { Course } from "../types";
import { courseColor, formatCredits } from "../utils";

interface Props {
  selected: Course[];
  max: number;
  totalCredits: number;
  updating: boolean;
  onRemove: (courseId: number) => void;
  onBrowse: (slot: number) => void;
  onClear: () => void;
}

export default function SelectedTray({
  selected,
  max,
  totalCredits,
  updating,
  onRemove,
  onBrowse,
  onClear,
}: Props) {
  return (
    <section className="pick-tray" aria-label="Selected electives">
      <div className="pick-tray-head">
        <div>
          <p className="section-kicker">Your plan</p>
          <h2>
            {selected.length} of {max} electives
            <span className="pick-credits">
              {totalCredits} credit{totalCredits === 1 ? "" : "s"}
            </span>
          </h2>
        </div>
        {updating ? (
          <span className="updating-label">
            <Loader2 size={14} className="spin" aria-hidden />
            Recalculating clashes
          </span>
        ) : selected.length ? (
          <button type="button" className="text-button tray-clear" onClick={onClear}>
            Clear plan
          </button>
        ) : (
          <span className="tray-hint">
            First pick unrestricted &middot; clash check after
          </span>
        )}
      </div>

      <div className="pick-slots">
        {Array.from({ length: max }).map((_, index) => {
          const course = selected[index];
          if (!course) {
            return (
              <button
                type="button"
                className={`pick-slot pick-empty ${index === 0 ? "is-first" : ""}`}
                key={`empty-${index}`}
                onClick={() => onBrowse(index)}
              >
                <span className="pick-empty-icon">
                  <Plus size={16} aria-hidden />
                </span>
                <span className="pick-empty-copy">
                  <strong>
                    {index === 0
                      ? "Pick your first elective"
                      : "Add another elective"}
                  </strong>
                  <span>
                    {index === 0
                      ? "No restrictions for pick one"
                      : "Only clash-free courses can be added"}
                  </span>
                </span>
              </button>
            );
          }

          const color = courseColor(index);
          const style = {
            "--course-bg": color.bg,
            "--course-border": color.border,
            "--course-ink": color.ink,
            "--course-solid": color.solid,
          } as CSSProperties;

          return (
            <div className="pick-slot pick-filled" key={course.id} style={style}>
              <div className="pick-filled-head">
                <span className="pick-order">
                  <span className="pick-order-dot" />
                  Pick {index + 1}
                </span>
                <button
                  type="button"
                  className="icon-button small"
                  onClick={() => onRemove(course.id)}
                  aria-label={`Remove ${course.title}`}
                >
                  <Trash2 size={14} aria-hidden />
                </button>
              </div>
              <p className="pick-title" title={course.title}>
                {course.title}
              </p>
              <div className="pick-meta">
                <span>{formatCredits(course.credits)}</span>
                <span>
                  {course.day_count} day{course.day_count === 1 ? "" : "s"}
                </span>
              </div>
              <p className="pick-schedule" title={course.schedule_label}>
                {course.schedule_label}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
