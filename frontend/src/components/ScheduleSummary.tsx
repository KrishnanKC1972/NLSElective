import { AlertTriangle, ArrowUpRight, Clock3, GraduationCap, Layers3 } from "lucide-react";
import type { Course } from "../types";
import { DAYS, DAY_SHORT, formatMinutes } from "../utils";

interface Props {
  selected: Course[];
  max: number;
  onAskLex: () => void;
}

export default function ScheduleSummary({ selected, max, onAskLex }: Props) {
  const totalCredits = selected.reduce(
    (total, course) => total + course.credits,
    0,
  );
  const totalMinutes = selected.reduce(
    (total, course) => total + course.weekly_minutes,
    0,
  );
  const sessionCount = selected.reduce(
    (total, course) => total + course.session_count,
    0,
  );
  const minutesByDay = DAYS.map((_, dayIndex) =>
    selected.reduce(
      (total, course) =>
        total +
        course.sessions
          .filter((session) => session.day_index === dayIndex)
          .reduce((sum, session) => sum + session.duration_min, 0),
      0,
    ),
  );
  const maxDayMinutes = Math.max(...minutesByDay, 1);
  const activeDays = minutesByDay.filter((minutes) => minutes > 0).length;
  const unscheduled = selected.filter((course) => !course.has_schedule);
  const remaining = Math.max(0, max - selected.length);

  return (
    <section className="panel insights-panel" aria-label="Plan insights">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">At a glance</p>
          <h2>Load &amp; balance</h2>
        </div>
        <span className={`plan-state ${remaining === 0 && selected.length ? "is-full" : ""}`}>
          {selected.length === 0
            ? "Not started"
            : remaining === 0
              ? "Plan full"
              : `${remaining} slot${remaining === 1 ? "" : "s"} left`}
        </span>
      </div>

      <div className="insight-metrics">
        <div className="insight-metric">
          <span className="insight-icon">
            <GraduationCap size={16} aria-hidden />
          </span>
          <strong>{totalCredits}</strong>
          <span>credits</span>
        </div>
        <div className="insight-metric">
          <span className="insight-icon">
            <Clock3 size={16} aria-hidden />
          </span>
          <strong>{formatMinutes(totalMinutes)}</strong>
          <span>class time / week</span>
        </div>
        <div className="insight-metric">
          <span className="insight-icon">
            <Layers3 size={16} aria-hidden />
          </span>
          <strong>
            {activeDays}
            <small>/6</small>
          </strong>
          <span>days on campus</span>
        </div>
      </div>

      <div className="load-bars">
        {DAYS.map((day, index) => {
          const minutes = minutesByDay[index];
          const width = minutes ? (minutes / maxDayMinutes) * 100 : 0;
          return (
            <div className="load-row" key={day}>
              <span className="load-day">{DAY_SHORT[day]}</span>
              <span className="load-track">
                <span
                  className={`load-fill ${minutes ? "" : "is-empty"}`}
                  style={{ width: `${Math.max(width, minutes ? 4 : 0)}%` }}
                />
              </span>
              <span className="load-value">
                {minutes ? formatMinutes(minutes) : "\u2014"}
              </span>
            </div>
          );
        })}
      </div>

      <div className="insight-footer">
        <p>
          {selected.length
            ? `${sessionCount} published class period${
                sessionCount === 1 ? "" : "s"
              } across your picks.`
            : "Choose electives to see your weekly balance."}
        </p>
        {unscheduled.length ? (
          <p className="insight-warning">
            <AlertTriangle size={13} aria-hidden />
            {unscheduled.length} course
            {unscheduled.length === 1 ? " has" : "s have"} no timetable data.
          </p>
        ) : null}
        <button type="button" className="text-button with-icon" onClick={onAskLex}>
          Ask Lex to review this plan
          <ArrowUpRight size={14} aria-hidden />
        </button>
      </div>
    </section>
  );
}
