export type ReminderUnit = "MINUTES" | "HOURS" | "DAYS" | "WEEKS";
export type ReminderAnchor = "START" | "END";

export interface Reminder {
  amount: number;
  unit: ReminderUnit;
  anchor: ReminderAnchor;
}

export type RecurrenceFreq = "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY";

export interface Recurrence {
  freq: RecurrenceFreq;
  interval: number;
  by_day: string[];
  count?: number | null;
  until?: string | null;
}

export interface ValidationIssue {
  field: string;
  code: string;
  severity: "ERROR" | "WARNING";
  message: string;
  blocks_export: boolean;
  suggestion?: string | null;
}

export interface FieldProvenance {
  field: string;
  provenance: "STATED" | "INFERRED" | "USER" | "DEFAULTED" | "MISSING" | "CONFLICTING";
}

export interface CanonicalEvent {
  id: string;
  title: string;
  category: string;
  start_date: string | null;
  start_time: string | null;
  end_date: string | null;
  end_time: string | null;
  timezone: string;
  all_day: boolean;
  location?: string | null;
  description?: string | null;
  organizer_name?: string | null;
  organizer_email?: string | null;
  url?: string | null;
  recurrence?: Recurrence | null;
  reminders: Reminder[];
  validation_status: "VALID" | "VALID_WITH_WARNINGS" | "REQUIRES_CLARIFICATION" | "INVALID";
  issues: ValidationIssue[];
  missing_fields: string[];
  ambiguity_flags: string[];
  provenance: FieldProvenance[];
  source_event_id?: string | null;
}

export interface ClarificationQuestion {
  id: string;
  event_id: string;
  field: string;
  question: string;
  suggested_answers: string[];
}

export interface AnalyzeResponse {
  batch_id: string;
  events: CanonicalEvent[];
  questions: ClarificationQuestion[];
  used_mock: boolean;
  model: string;
  status: string;
  total_events: number;
  valid_events: number;
  events_with_warnings: number;
  events_requiring_clarification: number;
}

export interface GenerateResponse {
  artifact_id: string;
  filename: string;
  event_count: number;
  ics_valid: boolean;
  validation_issues: { field: string; code: string; message: string }[];
}
