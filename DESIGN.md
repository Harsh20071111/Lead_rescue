# LeadSathi — System Architecture & Design Specification

This document provides a comprehensive technical overview of the current system architecture, database design, core engine logic, and feature workflows for **LeadSathi**.

---

## 1. System Overview

LeadSathi is a multi-tenant Real Estate SaaS application designed for agencies to capture leads, track property listings, auto-match buyer preferences with available inventory, and engage clients using automated communication channels.

### Tech Stack
*   **Backend:** Django (Python 3.13)
*   **Database:** PostgreSQL (Hosted on Neon DB)
*   **Task Queue:** Celery (leveraging Redis as the broker and result store) — primarily used for WhatsApp webhook processing. Import jobs run synchronously inline to avoid needing a paid worker.
*   **Storage:** Cloudinary (for property images, brochures, and raw import files)
*   **Frontend:** Django templates with HTML5, CSS3, Tailwind CSS (for styling), and HTMX (for dynamic, interactive UI updates without full page reloads)
*   **Integrations:** WhatsApp Business Cloud API (messaging/verification), Resend (emails)

---

## 2. Database & Data Model Design

The application enforces strict **multi-tenancy** scoped to an `Agency`. Most core models inherit from an agency-scoped design, managed by a custom `AgencyScopedManager`.

```mermaid
classDiagram
    class Agency {
        +id: int
        +name: varchar
        +whatsapp_display_name: varchar
    }
    class AgentProfile {
        +id: int
        +user: OneToOne(User)
        +agency: ForeignKey(Agency)
    }
    class Lead {
        +id: int
        +agency: ForeignKey(Agency)
        +assigned_agent: ForeignKey(AgentProfile)
        +name: varchar
        +phone: varchar
        +email: varchar
        +source: varchar (choices)
        +status: varchar (choices)
        +budget_min: decimal
        +budget_max: decimal
        +preferred_location: varchar
        +preferred_bhk: varchar
    }
    class Property {
        +id: int
        +agency: ForeignKey(Agency)
        +assigned_agent: ForeignKey(AgentProfile)
        +title: varchar
        +price: decimal
        +bhk: varchar (choices)
        +location: varchar
        +locality: varchar
        +city: varchar
        +listing_type: varchar (choices)
        +status: varchar (choices)
    }
    class PropertyImage {
        +id: int
        +property: ForeignKey(Property)
        +image: CloudinaryField
        +is_primary: boolean
    }
    class Task {
        +id: int
        +lead: ForeignKey(Lead)
        +assigned_agent: ForeignKey(AgentProfile)
        +due_date: datetime
        +is_completed: boolean
        +note: varchar
    }
    class Activity {
        +id: int
        +agency: ForeignKey(Agency)
        +lead: ForeignKey(Lead)
        +property: ForeignKey(Property)
        +activity_type: varchar (choices)
        +content: text
    }

    Agency "1" --> "many" AgentProfile
    Agency "1" --> "many" Lead
    Agency "1" --> "many" Property
    AgentProfile "1" --> "many" Lead
    AgentProfile "1" --> "many" Property
    Lead "1" --> "many" Task
    Property "1" --> "many" PropertyImage
    Lead "1" --> "many" Activity
    Property "1" --> "many" Activity
```

### Core Models

#### `Lead`
Represents prospective buyers or tenants.
*   **Preferences:** Tracks desired BHK, location, budget range (`budget_min` / `budget_max`), and property type.
*   **Lifecycle Statuses:** `New` &rarr; `Contacted` &rarr; `Qualified` &rarr; `Site Visit` &rarr; `Negotiation` &rarr; `Converted` &rarr; `Lost`.

#### `Property`
Represents real estate inventory.
*   **Attributes:** Address, city, locality, price, BHK, area size, amenities list (stored as a JSON list).
*   **Listing Types:** `Sale` or `Rent`.
*   **Status:** `Available`, `Pending`, `Sold`, `Rented`.

#### `Task` (Follow-Ups)
Core follow-up scheduling unit linked to a `Lead` and an `AgentProfile`.
*   **Attributes:** `due_date` (datetime), `is_completed` (boolean), `note` (character field).
*   **Reminders:** Scheduled via `send_followup_reminder` which dispatches email alerts to the assigned agent when tasks are near their due dates.

#### `Activity`
A persistent historical log of client engagement (Calls, Emails, Notes, WhatsApp messages, or Status changes).

---

## 3. Core Feature Workflows

### A. Lead Import System (Phase 5.5)

Designed to process bulk CSV/Excel uploads of leads or properties with zero-click automation. Import processing runs **synchronously inline** (using Celery's `apply()` instead of `delay()`) so it works without a background worker or Redis broker — ideal for Render's free tier.

```mermaid
sequenceDiagram
    actor Agent
    participant WebApp as Django View
    participant DB as Neon Postgres
    participant Cloudinary as Cloudinary Storage

    Agent->>WebApp: Upload CSV/Excel File
    WebApp->>Cloudinary: Save raw file & generate secure URL
    WebApp->>DB: Create ImportJob (Status: Pending)
    WebApp->>WebApp: Process import synchronously inline
    WebApp->>DB: Set status = Processing
    
    loop Every 100 rows (chunked)
        WebApp->>DB: Check if status == Canceled
        alt Is Canceled
            WebApp->>WebApp: Halt execution & Exit
        else Is Active
            WebApp->>DB: Create Leads/Properties
            WebApp->>DB: Update processed_rows, success/fail counters, and error_log
        end
    end

    WebApp->>DB: Set status = Completed / Failed
    WebApp-->>Agent: Redirect to Progress Page (shows final summary & error log)
```

#### 1. File Handling & Storage
To bridge the web process and background tasks, the system uses a custom `ImportFileStorage` backend:
*   In production, files are uploaded directly to **Cloudinary** (Raw storage). The public URL is saved in `file_url`.
*   Processing downloads the file via `requests.get(job.file_url)` directly into memory.

#### 2. Memory-Efficient Streaming
Files are processed in **100-row chunks** without loading the entire dataset into RAM:
*   **CSV:** Pandas `read_csv(chunksize=100)` — streaming iterator.
*   **XLSX:** `openpyxl.load_workbook(read_only=True)` + `iter_rows()` — row-by-row streaming, only 100-row DataFrame in memory at a time.
*   **XLS:** `xlrd` row iteration — same 100-row chunk pattern.

#### 3. Zero-Click Column Auto-mapping
Uploaded column headers are mapped to Django model fields automatically via Jaccard similarity and confidence scoring thresholds:
*   Normalized headers (lowercased, stripped of spaces/underscores) are compared to expected field aliases.
*   Maps standard columns (e.g., "Full Name", "Contact Number", "BHK Pref") to exact database fields (`name`, `phone`, `preferred_bhk`).

#### 4. Interruption / Cancellation Flow
*   When a user clicks "Cancel Import", it triggers a POST to `/imports/<id>/cancel/`, changing the database job status to `canceled`.
*   The processing loop checks `job.refresh_from_db()` before every 100-row chunk. If it detects `CANCELED`, it immediately terminates execution, saving progress up to that point.

---

### B. Auto-Matching Engine

Compares buyer preferences (Leads) with inventory (Properties) to calculate match scores.

*   **Scoring Metrics:**
    *   **BHK Preference (40% weight):** Exact match gets 100% score; adjacent configuration (e.g., ±1 BHK) gets partial 50% score.
    *   **Budget (35% weight):** Prices inside the lead's budget range get 100% score; prices within 15% tolerance outside the range get partial 50% score.
    *   **Location (25% weight):** Calculated by matching locality and city preferences.
*   **Threshold:** Matches with a combined score **> 0.30** are suggested to agents.

---

### C. WhatsApp Integration & Follow-Ups

Enables automatic lead capture and automated conversational flow.

#### 1. Inbound Conversation State Machine (`WhatsAppConversation`)
Route inbound messages through states to collect buyer profiles:
1.  `STARTED` &rarr; Send Welcome message, ask for name.
2.  `ASKED_NAME` &rarr; Save name, ask for budget.
3.  `ASKED_BUDGET` &rarr; Parse/save budget range, ask for BHK.
4.  `ASKED_BHK` &rarr; Parse/save BHK, ask for location.
5.  `ASKED_LOCATION` &rarr; Save location preference, create `Lead` in database, mark `COMPLETED`, and notify agent.

#### 2. Outbound WhatsApp Follow-Ups
Agents can trigger templates (such as `lead_follow_up`) directly from a lead's page. The system sends the message via Meta's WhatsApp API and logs an `Activity` entry on the lead.

---

## 4. Production Deployment Design (Render)

For smooth execution on Render's platform:
*   **Broker & Result Backend:** Both `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` default to `REDIS_URL`.
*   **SSL Configuration:** Automatic SSL parameters are initialized for `rediss://` secure Redis connections:
    ```python
    if CELERY_BROKER_URL.startswith("rediss://"):
        CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": "CERT_NONE"}
        CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": "CERT_NONE"}
    ```
*   **Import Processing:** Runs synchronously inline (Celery `apply()`) — no worker needed. Imports work on Render's free tier.
*   **WhatsApp Webhooks:** Use Celery `.delay()` for async processing. A paid Celery worker is required for real-time WhatsApp message handling.
*   **Celery Worker Execution (optional — for WhatsApp):**
    Runs as a standalone **Background Worker** on Render using the following startup sequence:
    `cd leadrescue && celery -A config worker --loglevel=info`

---

## 5. UI/UX Design Patterns

### A. Authentication & Session Management
*   **Remember Me:** Login form includes a "Keep me signed in" checkbox (default: on). When checked, session expires after 24 hours. When unchecked, session expires on browser close.
*   **Toast Notifications:** Django `messages` are rendered as fixed-position toast popups (top-right corner) that auto-disappear after 3 seconds with a slide-out animation.

### B. Dashboard & Leads List
*   **Color Palette:** Warm cream/beige/copper/charcoal — no generic blue/indigo.
*   **Typography:** Page titles in `Cormorant Garamond` (serif, bold), stat values in `Inter` (sans-serif, tabular-nums for alignment).
*   **Charts:**
    *   Dashboard uses Chart.js (bar + doughnut) with `responsive: true` to fill card containers.
    *   Leads list uses CSS-only charts (conic-gradient pie + flexbox bar chart).
    *   Cards use `display: flex; flex-direction: column` with `flex: 1` on the chart window so each chart fills its entire card.
*   **Stat Cards:** Show trend indicators (▲/▼/– with % vs prior 30-day period) when data is available.
*   **Indian Currency:** All monetary values formatted as `₹1.5 Cr`, `₹75 L`, `₹50,000` via `lead_extras` template tags.
*   **Status Colors:** Canonical color mapping defined in `lead_extras.py` (`STATUS_COLORS` dict) and CSS custom properties (`--sc-*`). Applied consistently across pie charts, source bars, table badges, and filter dropdowns.
*   **Avatars:** Colored-initial avatars from deterministic hash-based palette, replacing generic SVG cycle icons.

### C. Property Images (Cloudinary Integration)
*   Images are uploaded to Cloudinary via `uploader.upload()` and the returned `public_id` string is stored in the `CloudinaryField`. Raw file objects are never passed directly to the field.
*   Brochure PDFs follow the same pattern with `resource_type="raw"`.
*   On property deletion, `cloudinary.uploader.destroy()` cleans up the remote asset.
