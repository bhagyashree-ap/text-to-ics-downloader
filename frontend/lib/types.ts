export type ReminderUnit = "minutes" | "hours" | "days" | "weeks";

export interface Reminder {
  amount: number;
  unit: ReminderUnit;
}

export interface CalendarEvent {
  id: string;
  title: string;
  start: string | null; // ISO 8601 local wall time, or date for all-day
  end: string | null;
  all_day: boolean;
  timezone: string;
  location?: string | null;
  url?: string | null;
  description?: string | null;
  attendees: string[];
  rrule?: string | null;
  recurrence_phrase?: string | null;
  reminders: Reminder[];
  confidence: number;
  warnings: string[];
  source_text?: string | null;
  google_calendar_link?: string | null;
}

export interface ExtractResponse {
  events: CalendarEvent[];
  used_llm: boolean;
}
