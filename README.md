# SECOND SERVE
## A Smart Food Waste Rescue & NGO Redistribution Management System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://palletsprojects.com/p/flask/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.3-red.svg)](https://getbootstrap.com/)
[![Tests](https://img.shields.io/badge/Pytest-26%20Passed%20(100%25)-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Deployment-Localhost%20Only-success.svg)]()

> **Second Serve** is a locally running web application designed to eliminate avoidable food waste by connecting food donors (restaurants, hotels, college canteens) with registered NGOs for community redistribution. Built with a high-contrast, modern SaaS user interface strictly utilizing **Vibrant Red (`#FF0000`) and Crisp White (`#FFFFFF`)**, running 100% offline with zero CDN dependencies.

---

## 1. VISUAL IDENTITY & STRICT COLOR SYSTEM

The interface adheres to a high-contrast, ultra-clean SaaS aesthetic designed around **Vibrant Red (`#FF0000`)** and **Crisp White (`#FFFFFF`)**:

- **Primary Brand Accent:** `#FF0000` (Pure Red — primary action buttons, active navigation indicator, urgent deadline countdowns, floating match badges)
- **Primary Hover Accent:** `#CC0000` (Deep Crimson — interactive hover states and active borders)
- **Soft Tint Accent:** `#FFF1F1` (Blush Red — active sidebar pill backgrounds, explainable match callouts, subtle alert containers)
- **Canvas & Card Surfaces:** `#FFFFFF` cards, modals, and tables on a `#F9FAFB` (Off-white/Cool Gray) main workspace background
- **Primary Typography:** `#111827` (Charcoal near-black for high legibility)
- **Secondary Typography:** `#6B7280` (Neutral slate gray for labels, timestamps, and subtitles)
- **Borders & Dividers:** `#E5E7EB` (1px crisp borders, subtle elevation `0 1px 3px rgba(0,0,0,0.05)`)
- **Semantic Status Pills:**
  - *Available / Approved / Collected:* Soft Emerald (`#ECFDF5` bg, `#065F46` text)
  - *Urgent / Rejected / Expired:* Soft Red (`#FEF2F2` bg, `#DC2626` text)
  - *Pending / Reserved / Ready:* Soft Amber (`#FFFBEB` bg, `#92400E` text)
- **Typography & Tabular Numerals:** System geometric sans-serif (`'Inter', sans-serif`) with `font-variant-numeric: tabular-nums` for quantities, match percentages, and countdown timers.
- **Iconography:** Exclusively **locally bundled Lucide Icons** (`lucide.min.js`). No emojis are used as UI icons.

---

## 2. PRE-CONFIGURED DEMO ACCOUNTS

The application automatically seeds a realistic set of demo accounts on first run:

| Role | Account Name / Organization | Email | Password | Status | Permissions |
|---|---|---|---|:---:|---|
| **Administrator** | System Administrator (`Second Serve Core`) | `admin@secondserve.org` | `admin123` | **APPROVED** | NGO approvals, platform metrics, user & listing oversight |
| **Food Donor** | Chef Ramesh Sharma (`Taj Grand Kitchens`) | `donor@tajkitchens.com` | `donor123` | **APPROVED** | Publish listings, manage claims, mark food ready for pickup |
| **Food Donor 2**| Prof. Meera K. (`City College Canteen`) | `canteen@citycollege.edu`| `donor123` | **APPROVED** | Secondary donor in Koramangala with urgent dinner surplus |
| **Approved NGO** | Ananya Rao (`Feeding Hope Foundation`) | `ngo.approved@feedinghope.org` | `ngo123` | **APPROVED** | Browse food, view smart matches, submit and track claims |
| **Pending NGO** | Vikram Sen (`Care Meals Trust`) | `ngo.pending@caremeals.org` | `ngo123` | **PENDING** | View food & matches; claim locked until admin approval |

> *Tip:* On the login screen (`/login`), click the one-click demo filler buttons to instantly populate credentials for any role!

---

## 3. CORE FUNCTIONAL MODULES

### Module 1: User Registration & Role Access
- Role-based registration for **Food Donors** and **NGOs** with interactive toggle cards.
- NGOs are automatically created in `PENDING` verification status, requiring administrative verification before food claiming is unlocked.
- Password hashing via Werkzeug `pbkdf2:sha256` and session management via Flask-Login.

### Module 2: Surplus Food Listing Management
- Donors publish surplus food listings with title, category, description, quantity, unit (`Meals`, `kg`, `Packets`, `Boxes`, `Liters`), dietary type (`Vegetarian`, `Non-Vegetarian`), pickup address, locality, city, district, and collection cutoff.
- Automatic expiry handling: Listings whose collection deadline elapses are excluded from discovery and transitioned to `EXPIRED`.

### Module 3: NGO Dashboard & Food Discovery
- Real-time KPI stat row (`Available Surplus`, `Active Claims`, `Completed Collections`, `Total Rescued Food`).
- Filter & sort toolbar (text search, category dropdown, dietary toggle, location filter, sort by Highest Match / Earliest Deadline / Newest).
- 3-column responsive donation card grid with floating smart match badges, quantity badges, deadline indicators (highlighted in red if < 2 hours), and explainable match callouts.

### Module 4: Rule-Based Smart Matching Algorithm (`app/services/matching.py`)
Computes deterministic compatibility without external AI or third-party APIs using 4 weighted operational factors:

$$\text{Match Score} = (0.40 \times \text{Category}) + (0.25 \times \text{Location}) + (0.20 \times \text{Quantity}) + (0.15 \times \text{Urgency})$$

- **Category Compatibility (40%):** Exact match = 100, Compatible category = 75, Neutral = 50.
- **Location Compatibility (25%):** Same Locality = 100, Same City = 80, Same District = 60, Other = 30–40.
- **Quantity Suitability (20%):** Capacity ratio 0.8–1.25 = 100, Surplus = 85, Partial = 60, Extreme variance = 30.
- **Collection Deadline Urgency (15%):** Remaining time < 2h = 100, 2–6h = 85, 6–12h = 70, 12–24h = 50, > 24h = 30.
- **Score Classification:**
  - $85\text{--}100$: `Excellent Match`
  - $70\text{--}84$: `Good Match`
  - $50\text{--}69$: `Moderate Match`
  - $< 50$: `Low Match`
- Transparent explainability callouts displayed directly on each recommendation card.

### Module 5: Claim & Collection 4-Step Stepper Pipeline
A horizontal 4-step progress stepper tracks the physical food rescue:
1. **Claim Submitted (`PENDING`):** Approved NGO reserves listing. Prevents duplicate claims.
2. **Donor Accepted (`ACCEPTED`):** Donor reviews NGO details and confirms allocation.
3. **Ready for Collection (`READY_FOR_COLLECTION`):** Kitchen packs food containers at the pickup bay.
4. **Collected (`COLLECTED`):** Verified handover and final rescue completion.

### Module 6: Administrator Monitoring & Reports
- 8 KPI platform cards calculated live from SQLite records.
- **NGO Verification Queue:** Immediate Approve / Reject controls.
- Interactive local Chart.js visualizations (Donation Status Distribution doughnut and Category Volume bar chart).
- Full user directory with status toggling and donation oversight.

---

## 4. LOCAL INSTALLATION & RUNNING INSTRUCTIONS

### Prerequisites
- Windows 11 / 10 (or macOS / Linux)
- Python 3.10+ (tested on Python 3.10 and 3.12)
- Visual Studio Code or any terminal

### Step 1: Clone or Open Project Folder
```powershell
cd c:\Users\muham\Desktop\pr
```

### Step 2: Create and Activate Virtual Environment
```powershell
# Using Python's built-in venv
python -m venv .venv

# Activate on Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# (Or if using Command Prompt: .venv\Scripts\activate.bat)
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Application
```powershell
python run.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

*Note:* On initial startup, `seed_data.py` executes automatically, populating the SQLite database (`instance/second_serve.db`) with the pre-configured demo accounts and surplus food listings.

---

## 5. RUNNING AUTOMATED TESTS

The project contains a comprehensive automated test suite with **26 unit and integration tests** covering all modules:

```powershell
# Run the complete test suite with verbose output
.venv\Scripts\python.exe -m pytest -v
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\muham\Desktop\pr
collected 26 items

tests/test_admin.py::test_admin_dashboard_statistics PASSED              [  3%]
tests/test_admin.py::test_admin_ngo_approval PASSED                      [  7%]
tests/test_admin.py::test_admin_ngo_rejection PASSED                     [ 11%]
tests/test_admin.py::test_unauthorized_admin_access_blocked PASSED       [ 15%]
tests/test_auth.py::test_user_registration_donor PASSED                  [ 19%]
tests/test_auth.py::test_user_registration_ngo_status_pending PASSED     [ 23%]
tests/test_auth.py::test_duplicate_email_registration_rejected PASSED    [ 26%]
tests/test_auth.py::test_login_success_and_role_redirect PASSED          [ 30%]
tests/test_auth.py::test_invalid_login_rejected PASSED                   [ 34%]
tests/test_auth.py::test_role_access_boundaries PASSED                   [ 38%]
tests/test_claims.py::test_claim_submission_approved_ngo PASSED          [ 42%]
tests/test_claims.py::test_claim_submission_unapproved_ngo_rejected PASSED [ 46%]
tests/test_claims.py::test_duplicate_claim_prevention PASSED             [ 50%]
tests/test_claims.py::test_full_collection_workflow_steps PASSED         [ 53%]
tests/test_claims.py::test_reject_claim_releases_listing PASSED          [ 57%]
tests/test_claims.py::test_cancel_claim_by_ngo_releases_listing PASSED   [ 61%]
tests/test_donations.py::test_create_donation_success PASSED             [ 65%]
tests/test_donations.py::test_create_donation_invalid_quantity PASSED    [ 69%]
tests/test_donations.py::test_create_donation_past_deadline_rejected PASSED [ 73%]
tests/test_donations.py::test_edit_donation_unauthorized PASSED          [ 76%]
tests/test_donations.py::test_cancel_donation PASSED                     [ 80%]
tests/test_matching.py::test_category_scoring PASSED                     [ 84%]
tests/test_matching.py::test_location_scoring PASSED                     [ 88%]
tests/test_matching.py::test_urgency_scoring PASSED                      [ 92%]
tests/test_matching.py::test_composite_formula_calculation PASSED        [ 96%]
tests/test_matching.py::test_ranking_and_expired_exclusion PASSED        [100%]

====================== 26 passed in 52.07s ======================
```

---

## 6. PROJECT DIRECTORY ARCHITECTURE

```
pr/
|-- run.py                        # Application entry point & local development server
|-- config.py                     # Configuration settings & environment definitions
|-- seed_data.py                  # Seed script for realistic demo accounts and surplus food
|-- requirements.txt              # Production and test Python dependencies
|-- README.md                     # Comprehensive setup and user guide
|
|-- instance/
|   |-- second_serve.db           # SQLite database
|
|-- app/
|   |-- __init__.py               # Flask application factory, error handlers, Jinja filters
|   |-- extensions.py             # SQLAlchemy & Flask-Login extensions
|   |-- models.py                 # User, FoodListing, Claim, and AuditLog ORM models
|   |
|   |-- routes/
|   |   |-- __init__.py
|   |   |-- auth.py               # Authentication, registration, logout, role decorators
|   |   |-- donor.py              # Donor dashboard, create, edit, claims review, history
|   |   |-- ngo.py                # NGO dashboard, food discovery, smart matches, tracker
|   |   |-- admin.py              # Admin overview, NGO approvals, users, donations, claims
|   |   |-- main.py               # Landing route & role dispatching
|   |
|   |-- services/
|   |   |-- __init__.py
|   |   |-- matching.py           # 4-factor rule-based smart matching algorithm
|   |   |-- claim_service.py      # Claim transaction logic & 4-step stepper transitions
|   |   |-- listing_service.py    # Food listing CRUD, validations & auto-expiry checks
|   |   |-- report_service.py     # SQLite aggregation metrics & Chart.js data series
|   |
|   |-- static/
|   |   |-- css/
|   |   |   |-- style.css         # Strict #FF0000 / White design system & component styles
|   |   |-- js/
|   |   |   |-- app.js            # Lucide icon initializer, sidebar drawer, flash alerts
|   |   |-- images/
|   |   |   |-- uploads/          # Local storage for uploaded food pictures
|   |   |-- vendor/
|   |       |-- bootstrap/        # Local Bootstrap 5.3.3 CSS & JS (Zero CDNs)
|   |       |-- lucide/           # Local Lucide Icons UMD bundle (lucide.min.js)
|   |       |-- chartjs/          # Local Chart.js UMD bundle (chart.min.js)
|   |
|   |-- templates/
|       |-- base.html             # Global layout (fixed sidebar, header, flash toasts)
|       |-- auth/
|       |   |-- login.html        # Clean login card with 1-click demo filler buttons
|       |   |-- register.html     # Registration with interactive role selector cards
|       |-- donor/
|       |   |-- dashboard.html    # 4-column KPI cards & incoming claim review table
|       |   |-- create_donation.html # Form to publish food with location and deadline
|       |   |-- edit_donation.html   # Update available listings
|       |   |-- my_donations.html    # Filterable table of donor listings
|       |   |-- claims.html          # Claim requests review list
|       |   |-- claim_detail.html    # 4-step horizontal stepper & donor action console
|       |   |-- history.html         # Concluded rescues & lifetime impact archive
|       |-- ngo/
|       |   |-- dashboard.html    # NGO KPIs, active tracker banner, top recommendations
|       |   |-- discover.html     # Filter toolbar & 3-column donation card grid
|       |   |-- matches.html      # Algorithmic Smart Matches matrix with explainability
|       |   |-- donation_detail.html # Details, map location, and Claim modal
|       |   |-- my_claims.html    # Filterable claims overview
|       |   |-- tracker.html      # 4-step progress stepper & collection handoff
|       |-- admin/
|       |   |-- dashboard.html    # Platform metrics, NGO verification queue, Chart.js
|       |   |-- ngos.html         # NGO directory with instant Approve/Reject
|       |   |-- users.html        # User directory & account state management
|       |   |-- donations.html    # All listings oversight & administrative cancellation
|       |   |-- claims.html       # Platform claims monitoring table
|       |-- errors/
|           |-- 403.html          # Permission denied
|           |-- 404.html          # Resource not found
|           |-- 500.html          # Internal server error
|
|-- tests/
|   |-- __init__.py
|   |-- conftest.py               # In-memory SQLite fixtures & seed users
|   |-- test_auth.py              # Registration, login, role permissions tests
|   |-- test_donations.py         # Listing creation, validation, edit/cancel tests
|   |-- test_matching.py          # Factor weights, ranking, formula tests
|   |-- test_claims.py            # Claim creation, duplicate block, 4-step pipeline tests
|   |-- test_admin.py             # Stats, NGO approvals, access security tests
|
|-- docs/
    |-- UML_DIAGRAMS.md           # Use Case, Class, Sequence, Activity, State, ER diagrams
    |-- TEST_CASES.md             # Test case specifications and execution verification report
```

---

## 7. SYSTEM DESIGN & DOCUMENTATION DELIVERABLES

Comprehensive UML and engineering diagrams are provided in [`docs/UML_DIAGRAMS.md`](file:///c:/Users/muham/Desktop/pr/docs/UML_DIAGRAMS.md):
1. **Use Case Diagram:** Actors (Food Donor, Registered NGO, Admin) and system boundary interactions.
2. **Class Diagram:** Domain models (`User`, `FoodListing`, `Claim`, `AuditLog`) with associations and method signatures.
3. **Sequence Diagram:** Chronological interaction flow for browsing, claiming, donor acceptance, and collection confirmation.
4. **Activity Diagram:** End-to-end operational lifecycle from surplus preparation to community distribution.
5. **State Machine Diagram:** Valid transitions for food claims (`PENDING` $\rightarrow$ `ACCEPTED` $\rightarrow$ `READY_FOR_COLLECTION` $\rightarrow$ `COLLECTED`).
6. **Entity-Relationship (ER) Diagram:** Complete database relational schema with cardinality and foreign key constraints.

---

## 8. ACADEMIC & PROJECT VERIFICATION

- **Academic Subject:** Software Engineering & System Design
- **Localhost Compliance:** 100% offline-first. Bootstrap, Lucide, and Chart.js assets are locally served from `/static/vendor/`.
- **Database Integrity:** Foreign keys, cascades, unique constraints, and atomic transactions prevent duplicate or conflicting claims.
- **Rule-Based Algorithm:** Transparent, explainable scoring running in pure Python without external dependencies.
