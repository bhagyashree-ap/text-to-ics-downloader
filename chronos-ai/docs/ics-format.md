# ICS Format Notes (RFC 5545)

Generated with the `icalendar` library — never by string concatenation and never by
the LLM. The library handles escaping (commas, semicolons, backslashes, newlines) and
line folding.

## Calendar level

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Chronos AI//Calendar Generator//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:<calendar name>
...
END:VCALENDAR
```

## Timed event

Local wall time with the IANA timezone attached:
```
DTSTART;TZID=America/New_York:20261015T090000
DTEND;TZID=America/New_York:20261015T100000
```
The validator confirms the parsed **local** time equals the canonical local time
(not merely the UTC instant).

## All-day event (exclusive end)

A one-day event on Dec 25 serializes as:
```
DTSTART;VALUE=DATE:20261225
DTEND;VALUE=DATE:20261226      ← exclusive end (next day)
```

## Deadlines

A deadline is a single instant: `DTSTART == DTEND`. No fabricated duration.

## Reminders → VALARM

```
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Reminder: <title>
TRIGGER:-P1D            ← 1 day before start
END:VALARM
```
End-anchored reminders use `TRIGGER;RELATED=END`. An embedded alarm *requests* an
alarm in the destination app; appearance varies across Google/Apple/Outlook.

## Recurrence → RRULE

```
RRULE:FREQ=WEEKLY;BYDAY=MO;UNTIL=20261221T235959Z
```
Recurrence is validated before serialization (`COUNT` and `UNTIL` are mutually
exclusive; weekday codes must be valid). The local time + timezone are preserved so
the wall-clock time stays constant across DST.

## Round-trip guarantee

Every generated file is parsed back and compared to the canonical input events
(count, UID match, title, local start, all-day exclusivity, VALARM count). A file
that fails is rejected and never served.
