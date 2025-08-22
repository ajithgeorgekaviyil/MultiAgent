# Multi-Agent Support System

A minimal **Django + OpenAI Agents SDK** demo that showcases **multi-agent orchestration** support.

Agents:

- **Triage** – routes each user turn to the right specialist
- **Course Advisor** – course selection & academic planning and non-related queries
- **Scheduling Assistant** – class times, exam schedules, and key academic dates (concise, factual sentences)
- **University Poet** – haiku about campus/social life only

The project demonstrates **triage**, **agent handoffs**, **tool calls**, **session memory**, and a **single-page UI**.

---

## Priority & Handoff Policy (Design)

Triage is consulted **every turn**, and specialists execute in a deterministic priority order:

**Poet → Scheduler → Advisor**

Intent rules:

- **Poet** participates only when the user asks for a poem/haiku/limerick and the topic is campus or student social life.
- **Scheduler** participates when there’s an explicit date/time/schedule ask (e.g., *when, date, deadline, add/drop, midterms, finals*), and answers in concise, factual sentences using the schedule tool.
- **Advisor** participates for questions about courses, electives, prerequisites, credits, requirements, or planning

**Non-related / unclear requests** → **fallback to Course Advisor** for a brief capability clarification.  

---

## Setup & Installation

### Prerequisites
- **Python 3.10+**
- **Django 5+**
- A valid **OpenAI API key**

### Installation

- git clone https://github.com/ajithgeorgekaviyil/MultiAgent.git
- cd MultiAgent
- python -m venv .venv
# macOS/Linux:
- source .venv/bin/activate         
# Windows (PowerShell): 
- .\.venv\Scripts\Activate.ps1
- ```pip install -r requirements.txt```

### Environment Variables

Create a .env file at the project root:
SECRET_KEY=your_django_secret_key_here         # any non-empty string works
DJANGO_DEBUG=False
OPENAI_API_KEY=your_openai_api_key_here
ALLOWED_HOSTS=127.0.0.1,localhost


### Running the Project

Backend
Start the Django server:
```python manage.py runserver```

Frontend
Open your browser at:
http://127.0.0.1:8000/

Type a message in the chat box.
Session ID is preserved across turns.
Messages display with the agent name (CourseAdvisor, UniversityPoet, SchedulingAssistant).
Clear chat resets the session.

### Tools & Data

Course Advisor recommend_courses(interest, limit, type_filter, level) – mocked course catalog (UG/PG, core/elective)
summarize_text(text) – one-sentence summaries via OpenAI Responses API
Scheduling Assistant lookup_schedule() – mocked academic calendar (term start, add/drop, midterms, finals, graduation)
All dependencies are public/open-source; no secrets are committed. OPENAI_API_KEY is read from the environment.

### Test Scenarios

🔹 Smoke Tests
When are finals? → Scheduling Assistant responds with exam dates.
Suggest electives in data science → Course Advisor suggests electives.
Write a haiku about dorm life → University Poet responds in haiku.
🔹 Handoff Tests
When are finals and suggest data science electives too
→ Triage → Scheduling Assistant → Course Advisor (handoff chain).
Give me exam dates and a haiku about campus nights
→ Triage → University Poet → Scheduling Assistant.
🔹 Memory Test
User: I’m interested in data science
User: Based on that, what electives fit my background in Python?
User: When are the finals for the courses you suggested?
→ Advisor remembers interest in data science.
🔹 Responses API Tool Test (Summarise Scenario)
User: Summarize your Data Science recommendations in one concise sentence.
→ CourseAdvisor calls the summarize tool (via OpenAI Responses API)) → Provide recommendations in one sentence.
🔹 Negative / Edge Cases
Tell me tomorrow’s weather
→ Advisor politely clarifies scope (no OOS agent, fallback to Advisor).

### Automated Tests 

Basic integration tests are included in chat_api/tests.py.
Run with:
```python manage.py test -v 2```


### Potential Improvements
Introduce a semantic approach to intent detection and routing.
Adopt Django REST Framework (DRF) for clean API endpoints, better decoupling from the UI, and easier automated testing.
Apply security tokens (JWT or signed session tokens for API usage),

### Project Coverage
# Backend (Django)
OpenAI Agents SDK and Responses API
Triage + 3 specialists (distinct personas)
Routing & handoffs (chain surfaced in responses)
Tool calls: recommend_courses, lookup_schedule, summarize_text
Session memory via SQLite session storage keyed by session id
API key from env

# Frontend
Single page (send, clear)
Displays agent name + message
Preserves session id
