# SECOND SERVE: SYSTEM ARCHITECTURE & UML SPECIFICATIONS

This document outlines the software engineering and system design specifications for **Second Serve**, a Smart Food Waste Rescue and NGO Redistribution Management System.

---

## 1. Use Case Diagram

```mermaid
flowchart LR
    Donor["Food Donor"]
    NGO["Registered NGO"]
    Admin["System Administrator"]

    subgraph Authentication ["Authentication & Access"]
        UC_Reg["Register Account"]
        UC_Login["Login / Logout"]
    end

    subgraph DonationModule ["Surplus Food Donation"]
        UC_Create["Publish Food Listing"]
        UC_Edit["Edit Available Listing"]
        UC_CancelListing["Cancel Listing"]
        UC_ViewListings["View My Donations"]
    end

    subgraph DiscoveryMatching ["Food Discovery & Matching"]
        UC_Discover["Search & Filter Surplus Food"]
        UC_Matches["View Rule-Based Smart Matches"]
        UC_ViewDetail["View Food & Donor Details"]
    end

    subgraph ClaimTracking ["Claim & Collection Workflow"]
        UC_Claim["Submit Claim Request"]
        UC_AcceptClaim["Accept / Reject Claim"]
        UC_MarkReady["Mark Food Ready for Pickup"]
        UC_ConfirmCollected["Confirm Food Collected"]
        UC_CancelClaim["Cancel Pending Claim"]
    end

    subgraph AdminModule ["Administration & Oversight"]
        UC_ApproveNGO["Approve / Reject NGO"]
        UC_ManageUsers["Manage User Accounts"]
        UC_AdminDonations["Monitor & Cancel Inappropriate Listings"]
        UC_AdminReports["View Platform Analytics & Charts"]
    end

    Donor --> UC_Reg
    Donor --> UC_Login
    Donor --> UC_Create
    Donor --> UC_Edit
    Donor --> UC_CancelListing
    Donor --> UC_ViewListings
    Donor --> UC_AcceptClaim
    Donor --> UC_MarkReady
    Donor --> UC_ConfirmCollected

    NGO --> UC_Reg
    NGO --> UC_Login
    NGO --> UC_Discover
    NGO --> UC_Matches
    NGO --> UC_ViewDetail
    NGO --> UC_Claim
    NGO --> UC_ConfirmCollected
    NGO --> UC_CancelClaim

    Admin --> UC_Login
    Admin --> UC_ApproveNGO
    Admin --> UC_ManageUsers
    Admin --> UC_AdminDonations
    Admin --> UC_AdminReports
```

---

## 2. Class Diagram

```mermaid
classDiagram
    class User {
        +int id
        +string name
        +string email
        +string password_hash
        +string role
        +string phone
        +string organization_name
        +string address
        +string locality
        +string city
        +string district
        +string verification_status
        +bool is_active
        +datetime created_at
        +set_password(password)
        +check_password(password) bool
        +is_admin bool
        +is_donor bool
        +is_ngo bool
        +is_approved_ngo bool
    }

    class FoodListing {
        +int id
        +int donor_id
        +string title
        +string category
        +text description
        +float quantity
        +string unit
        +string food_type
        +string image_filename
        +string location
        +string locality
        +string city
        +string district
        +datetime available_from
        +datetime collection_deadline
        +string status
        +datetime created_at
        +datetime updated_at
        +is_expired bool
        +remaining_hours float
        +remaining_time_str string
        +is_urgent bool
        +active_claim Claim
    }

    class Claim {
        +int id
        +int listing_id
        +int recipient_id
        +string status
        +text notes
        +string rejection_reason
        +datetime created_at
        +datetime updated_at
        +datetime collected_at
        +step_number int
        +is_active bool
    }

    class AuditLog {
        +int id
        +int user_id
        +string action
        +string entity_type
        +int entity_id
        +text details
        +datetime created_at
    }

    class MatchingService {
        +calculate_category_score(ngo, listing) float
        +calculate_location_score(ngo, listing) float
        +calculate_quantity_score(ngo, listing, req_qty) float
        +calculate_urgency_score(listing) float
        +calculate_match_score(ngo, listing) dict
        +get_ranked_recommendations(ngo, listings) list
    }

    User "1" --> "*" FoodListing : creates (as Donor)
    User "1" --> "*" Claim : submits (as NGO)
    FoodListing "1" --> "*" Claim : has claims
    User "1" --> "*" AuditLog : generates
    MatchingService ..> User : consumes
    MatchingService ..> FoodListing : scores
```

---

## 3. Sequence Diagram: Claiming & Collection Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor NGO as Approved NGO
    participant Web as Web UI / Browser
    participant App as Flask Application
    participant Match as Matching Service
    participant Svc as Claim Service
    participant DB as SQLite Database
    actor Donor as Food Donor

    NGO->>Web: Opens Food Discovery / Smart Matches
    Web->>App: GET /ngo/matches
    App->>Match: get_ranked_recommendations(ngo_user)
    Match->>DB: Query available non-expired listings
    DB-->>Match: Return Food Listings
    Match-->>App: Return ranked recommendations with explanations
    App-->>Web: Render Matches UI with Match % Badges

    NGO->>Web: Clicks "Claim Donation" (with pickup notes)
    Web->>App: POST /ngo/donations/{id}/claim
    App->>Svc: create_claim(listing_id, ngo_user, notes)
    Svc->>DB: Check NGO status == 'APPROVED'
    Svc->>DB: Check Listing status == 'AVAILABLE' and not expired
    Svc->>DB: Atomically UPDATE listing status = 'RESERVED'
    Svc->>DB: INSERT Claim record (status = 'PENDING')
    DB-->>Svc: Commit Transaction
    Svc-->>App: Claim Created (Step 1)
    App-->>Web: Redirect to Collection Tracker

    Donor->>Web: Opens Donor Claim Requests
    Web->>App: GET /donor/claims/{id}
    App-->>Web: Render Claim Details (Step 1: PENDING)
    Donor->>Web: Clicks "Accept Claim"
    Web->>App: POST /donor/claims/{id}/accept
    App->>Svc: accept_claim(claim_id, donor_user)
    Svc->>DB: UPDATE Claim status = 'ACCEPTED' (Step 2)
    DB-->>App: Commit
    App-->>Web: Updated to Step 2: ACCEPTED

    Donor->>Web: Packs food & clicks "Mark Ready for Pickup"
    Web->>App: POST /donor/claims/{id}/ready
    App->>Svc: mark_ready_for_collection(claim_id, donor_user)
    Svc->>DB: UPDATE Claim status = 'READY_FOR_COLLECTION' (Step 3)
    DB-->>App: Commit
    App-->>Web: Updated to Step 3: READY_FOR_COLLECTION

    NGO->>Web: Collects food at kitchen & confirms pickup
    Web->>App: POST /ngo/claims/{id}/confirm-collected
    App->>Svc: confirm_collected(claim_id, ngo_user)
    Svc->>DB: UPDATE Claim status = 'COLLECTED' (Step 4, timestamp)
    Svc->>DB: UPDATE Listing status = 'COLLECTED'
    DB-->>App: Commit
    App-->>Web: Updated to Step 4: COLLECTED (Rescue Complete)
```

---

## 4. Activity Diagram: Food Donation & Collection Lifecycle

```mermaid
flowchart TD
    Start([Food Donor has Surplus Food]) --> CreateListing[Donor publishes listing with Title, Quantity, Location, and Deadline]
    CreateListing --> ValidateInput{Valid Inputs & Future Deadline?}
    ValidateInput -- No --> ShowError[Display Validation Error]
    ShowError --> CreateListing
    ValidateInput -- Yes --> SaveListing[Listing saved as AVAILABLE in SQLite]
    
    SaveListing --> Discovery[Available in NGO Discovery & Smart Matching]
    Discovery --> MatchCheck{Smart Matching Ranking}
    MatchCheck --> Scored[Ranked by Category 40%, Location 25%, Qty 20%, Urgency 15%]
    
    Scored --> NGOBrowse[NGO views donation card with Match Score & Reason]
    NGOBrowse --> NGOClaim{Approved NGO claims donation?}
    NGOClaim -- Deadline Passes --> Expired[System auto-expires listing] --> EndExpired([Listing Expired])
    NGOClaim -- Yes --> ReserveListing[Listing reserved; Claim created as PENDING]
    
    ReserveListing --> DonorReview{Donor Reviews Claim}
    DonorReview -- Reject --> RejectClaim[Claim marked REJECTED; Listing reverted to AVAILABLE]
    RejectClaim --> Discovery
    DonorReview -- Accept --> AcceptClaim[Claim marked ACCEPTED; Kitchen packs food]
    
    AcceptClaim --> MarkReady[Donor marks READY_FOR_COLLECTION]
    MarkReady --> Transport[NGO transport arrives at pickup bay]
    Transport --> Handover[Food inspected and transferred to NGO]
    Handover --> ConfirmCollection[Collection confirmed; Claim & Listing marked COLLECTED]
    ConfirmCollection --> EndSuccess([Food Rescued & Redistributed])
```

---

## 5. State Machine Diagram: Claim Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING : NGO Submits Claim (Listing becomes RESERVED)
    
    PENDING --> ACCEPTED : Donor Accepts Claim
    PENDING --> REJECTED : Donor Rejects Claim (Listing restored to AVAILABLE)
    PENDING --> CANCELLED : NGO Cancels Claim (Listing restored to AVAILABLE)
    
    ACCEPTED --> READY_FOR_COLLECTION : Donor marks packed and ready at pickup bay
    ACCEPTED --> CANCELLED : Cancelled before dispatch (Listing restored)
    
    READY_FOR_COLLECTION --> COLLECTED : Volunteer arrives & collection confirmed
    
    REJECTED --> [*]
    CANCELLED --> [*]
    COLLECTED --> [*] : Completed Food Rescue
```

---

## 6. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USERS ||--o{ FOOD_LISTINGS : creates
    USERS ||--o{ CLAIMS : receives
    USERS ||--o{ AUDIT_LOGS : triggers
    FOOD_LISTINGS ||--o{ CLAIMS : receives_for

    USERS {
        int id PK
        string name
        string email UK
        string password_hash
        string role
        string phone
        string organization_name
        string address
        string locality
        string city
        string district
        string verification_status
        boolean is_active
        datetime created_at
    }

    FOOD_LISTINGS {
        int id PK
        int donor_id FK
        string title
        string category
        text description
        float quantity
        string unit
        string food_type
        string image_filename
        string location
        string locality
        string city
        string district
        datetime available_from
        datetime collection_deadline
        string status
        datetime created_at
        datetime updated_at
    }

    CLAIMS {
        int id PK
        int listing_id FK
        int recipient_id FK
        string status
        text notes
        string rejection_reason
        datetime created_at
        datetime updated_at
        datetime collected_at
    }

    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string entity_type
        int entity_id
        text details
        datetime created_at
    }
```
