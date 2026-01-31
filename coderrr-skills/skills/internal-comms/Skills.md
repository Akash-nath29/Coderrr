---
name: internal-comms
description: Write internal communications like status reports, newsletters, announcements, and team updates. Use this skill when the user needs to draft status reports, write team newsletters, create announcements, compose meeting summaries, or generate internal documentation.
---

This skill helps create professional internal communications. It generates well-structured content for various internal communication needs with appropriate tone and formatting.

The user wants to write internal communications. They may provide context, key points, or ask for a specific type of document.

## Approach

When creating internal communications:
1. **Choose type**: Identify the communication type
2. **Gather context**: Collect key information and audience
3. **Generate**: Use appropriate tool for content type
4. **Format**: Export in desired format

## Tools

### status_report

Generates project or team status reports.

```bash
python tools/status_report.py --project <name> --period <period> --data <json> [--format <markdown|html>]
```

**Arguments:**
- `--project` (required): Project/team name
- `--period` (required): Reporting period (e.g., "Week 5", "January 2024")
- `--data` (required): Report data JSON
- `--format` (optional): Output format (default: markdown)

**Data JSON:**
```json
{
  "highlights": ["Completed feature X", "Launched beta"],
  "progress": {"tasks_completed": 15, "tasks_remaining": 8},
  "blockers": ["Waiting on API access"],
  "next_steps": ["Begin testing phase"],
  "metrics": {"velocity": 42, "bugs_fixed": 7}
}
```

**When to use:**
- Weekly/monthly status updates
- Project progress reports
- Team performance summaries

---

### newsletter

Creates internal newsletters.

```bash
python tools/newsletter.py --title <title> --sections <json> [--format <markdown|html>]
```

**Arguments:**
- `--title` (required): Newsletter title
- `--sections` (required): Section content JSON
- `--format` (optional): Output format

**Sections JSON:**
```json
[
  {"type": "intro", "content": "Welcome message..."},
  {"type": "highlight", "title": "Big Win", "content": "We achieved..."},
  {"type": "updates", "items": ["Update 1", "Update 2"]},
  {"type": "spotlight", "name": "Jane Doe", "role": "Engineer", "content": "Achievements..."},
  {"type": "upcoming", "events": [{"date": "Feb 15", "title": "All-hands"}]}
]
```

**When to use:**
- Weekly team newsletters
- Monthly company updates
- Department communications

---

### announcement

Creates formal announcements.

```bash
python tools/announcement.py --type <type> --subject <subject> --content <json> [--urgency <level>]
```

**Arguments:**
- `--type` (required): Announcement type - `general`, `policy`, `event`, `change`, `launch`
- `--subject` (required): Announcement subject
- `--content` (required): Content details JSON
- `--urgency` (optional): Urgency level - `normal`, `important`, `urgent`

**Content JSON:**
```json
{
  "summary": "Brief summary of announcement",
  "details": "Full details and context...",
  "action_items": ["Review by Friday", "Submit feedback"],
  "contact": "jane@company.com",
  "effective_date": "2024-02-01"
}
```

**When to use:**
- Policy updates
- Organizational changes
- Product launches
- Event announcements

---

### meeting_summary

Generates meeting summaries.

```bash
python tools/meeting_summary.py --title <title> --date <date> --data <json>
```

**Arguments:**
- `--title` (required): Meeting title
- `--date` (required): Meeting date
- `--data` (required): Meeting data JSON

**Data JSON:**
```json
{
  "attendees": ["Alice", "Bob", "Charlie"],
  "agenda": ["Q1 planning", "Budget review"],
  "discussion": [
    {"topic": "Q1 Goals", "summary": "Agreed on 3 key objectives..."},
    {"topic": "Budget", "summary": "Approved $50k allocation..."}
  ],
  "decisions": ["Launch in March", "Hire 2 engineers"],
  "action_items": [
    {"owner": "Alice", "task": "Draft proposal", "due": "Feb 10"}
  ],
  "next_meeting": "Feb 15, 2024"
}
```

**When to use:**
- Team meeting notes
- Stakeholder meeting summaries
- Decision documentation

---

### template

Generates reusable communication templates.

```bash
python tools/template.py --type <type> [--customize <json>]
```

**Arguments:**
- `--type` (required): Template type - `status`, `newsletter`, `announcement`, `meeting`, `email`
- `--customize` (optional): Customization options

**When to use:**
- Setting up recurring communications
- Standardizing team output
- Creating document templates

## Common Patterns

### Weekly Status Report
```bash
python tools/status_report.py --project "Backend Team" --period "Week 5" --data '{"highlights": ["Deployed v2.0", "Fixed 12 bugs"], "progress": {"tasks_completed": 18, "tasks_remaining": 5}, "blockers": [], "next_steps": ["Performance testing"]}'
```

### Team Newsletter
```bash
python tools/newsletter.py --title "Engineering Weekly #12" --sections '[{"type": "intro", "content": "Great week everyone!"}, {"type": "highlight", "title": "Launch Success", "content": "Product v2.0 is live!"}, {"type": "upcoming", "events": [{"date": "Feb 20", "title": "Hackathon"}]}]' --format html
```

### Policy Announcement
```bash
python tools/announcement.py --type policy --subject "Remote Work Update" --content '{"summary": "New hybrid policy starting March", "details": "We are updating our remote work policy...", "effective_date": "2024-03-01"}' --urgency important
```

## Writing Guidelines

### Tone
- **Status reports**: Factual, concise, data-driven
- **Newsletters**: Engaging, positive, inclusive
- **Announcements**: Clear, direct, professional
- **Meeting notes**: Structured, action-oriented

### Structure
- Lead with key information
- Use bullet points for lists
- Include clear action items
- Provide contact for questions

### Best Practices
1. Keep it scannable
2. Highlight important dates
3. Use consistent formatting
4. Include relevant links
5. Proofread before sending

## Dependencies

Uses Python standard library only.
