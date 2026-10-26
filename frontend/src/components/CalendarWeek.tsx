import type { CSSProperties } from "react";
import { CalendarDays, Clock3, MapPin } from "lucide-react";
import type { Block, Course } from "../types";
import { DAYS, DAY_SHORT, courseColor, formatMinutes } from "../utils";

const START_MIN = 9 * 60;
const END_MIN = 19 * 60;
const PIXELS_PER_MINUTE = 1;
const HOURS = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19];

interface Props {
  selected: Course[];
  onOpenCourse: (course: Course) => void;
  onBrowse: () => void;
}

interface CalendarEvent {
  course: Course;
  block: Block;
  colorIndex: number;
}

function hourLabel(hour: number): string {
  const suffix = hour < 12 ? "AM" : "PM";
  return `${hour % 12 || 12} ${suffix}`;
}

function roomsLabel(block: Block): string {
  if (!block.classrooms.length) {
    return "Room TBA";
  }
  return block.classrooms.length > 1
    ? `${block.classrooms.length} rooms listed`
    : block.classrooms[0];
}

export default function CalendarWeek({
  selected,
  onOpenCourse,
  onBrowse,
}: Props) {
  const events: CalendarEvent[] = selected.flatMap((course, colorIndex) =>
    course.blocks.map((block) => ({ course, block, colorIndex })),
  );
  const minutesByDay = new Map<number, number>();
  for (const course of selected) {
    for (const session of course.sessions) {
      minutesByDay.set(
        session.day_index,
        (minutesByDay.get(session.day_index) ?? 0) + session.duration_min,
      );
    }
  }
  const unscheduled = selected.filter((course) => !course.has_schedule);
  const totalMinutes = selected.reduce(
    (total, course) => total + course.weekly_minutes,
    0,
  );

  return (
    <section className="panel calendar-panel" aria-label="Weekly calendar">
      <div className="panel-heading calendar-heading">
        <div>
          <p className="section-kicker">Week view</p>
          <h2>Your timetable</h2>
        </div>
        <div className="calendar-meta">
          <span>
            <Clock3 size={13} aria-hidden />
            {formatMinutes(totalMinutes)} / week
          </span>
          <span className="calendar-zone">IST</span>
        </div>
      </div>

      <div className="calendar-scroll">
        <div className="calendar">
          <div className="calendar-header">
            <div className="calendar-gutter-header" />
            {DAYS.map((day, index) => {
              const dayMinutes = minutesByDay.get(index) ?? 0;
              return (
                <div
                  className={`calendar-day-head ${
                    dayMinutes ? "has-class" : ""
                  }`}
                  key={day}
                >
                  <span>{DAY_SHORT[day]}</span>
                  {dayMinutes ? (
                    <em>{formatMinutes(dayMinutes)}</em>
                  ) : (
                    <em className="free">free</em>
                  )}
                </div>
              );
            })}
          </div>

          <div className="calendar-body">
            <div className="calendar-gutter">
              {HOURS.map((hour) => (
                <span
                  className="time-label"
                  key={hour}
                  style={{
                    top: (hour * 60 - START_MIN) * PIXELS_PER_MINUTE,
                  }}
                >
                  {hourLabel(hour)}
                </span>
              ))}
            </div>

            {Array.from({ length: 6 }).map((_, dayIndex) => (
              <div className="calendar-day" key={dayIndex}>
                {HOURS.map((hour) => (
                  <span
                    className="hour-line"
                    key={hour}
                    style={{
                      top: (hour * 60 - START_MIN) * PIXELS_PER_MINUTE,
                    }}
                  />
                ))}

                {events
                  .filter((event) => event.block.day_index === dayIndex)
                  .map((event) => {
                    const color = courseColor(event.colorIndex);
                    const top =
                      (event.block.start_min - START_MIN) *
                      PIXELS_PER_MINUTE;
                    const height = Math.min(
                      event.block.end_min - event.block.start_min,
                      END_MIN - event.block.start_min,
                    );
                    const compact = height < 56;
                    const style = {
                      top,
                      height,
                      background: color.bg,
                      borderLeftColor: color.border,
                      color: color.ink,
                    } as CSSProperties;
                    return (
                      <button
                        type="button"
                        className={`calendar-event ${compact ? "is-compact" : ""}`}
                        style={style}
                        key={`${event.course.id}-${event.block.day}-${event.block.start_min}`}
                        onClick={() => onOpenCourse(event.course)}
                        title={`${event.course.title} \u00b7 ${event.block.day} ${event.block.time_label} \u00b7 ${roomsLabel(event.block)}`}
                      >
                        <span className="event-title">
                          {event.course.title}
                        </span>
                        <span className="event-time">
                          {event.block.time_label}
                        </span>
                        {!compact ? (
                          <span className="event-room">
                            <MapPin size={10} aria-hidden />
                            {roomsLabel(event.block)}
                          </span>
                        ) : null}
                      </button>
                    );
                  })}
              </div>
            ))}

            {!events.length ? (
              <div className="calendar-empty">
                <span className="calendar-empty-icon">
                  <CalendarDays size={22} aria-hidden />
                </span>
                <strong>
                  {selected.length
                    ? "No published class slots"
                    : "Your week is wide open"}
                </strong>
                <p>
                  {selected.length
                    ? "The selected elective has no timetable in the workbook."
                    : "Add an elective and every published class block appears here."}
                </p>
                {!selected.length ? (
                  <button
                    type="button"
                    className="small-button"
                    onClick={onBrowse}
                  >
                    Browse electives
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="calendar-footer">
        <div className="calendar-legend">
          {selected.map((course, index) => (
            <span className="legend-item" key={course.id}>
              <span
                className="legend-dot"
                style={{ background: courseColor(index).solid }}
              />
              {course.title}
            </span>
          ))}
          {!selected.length ? (
            <span className="legend-placeholder">
              Selected courses will be colour-coded here.
            </span>
          ) : null}
        </div>
        {unscheduled.length ? (
          <p className="calendar-note">
            {unscheduled.length} selected course
            {unscheduled.length === 1 ? " has" : "s have"} no published
            timetable. Check with the academic office.
          </p>
        ) : (
          <p className="calendar-note">
            All published slots are shown. Some electives list more than one
            slot sequence.
          </p>
        )}
      </div>
    </section>
  );
}
