# SECOND SERVE: AUTOMATED TEST CASE MATRIX & VERIFICATION REPORT

This document specifies the test cases implemented for the **Second Serve** application, covering Authentication, Food Donation Management, Rule-Based Smart Matching, Claim & Collection Workflows, and Administration.

All **26 automated test cases** are executed via `pytest` against an in-memory SQLite database.

---

## 1. Test Summary

| Test Suite | File | Test Count | Status |
|---|---|:---:|:---:|
| Authentication & Access Control | `tests/test_auth.py` | 6 | **PASS (100%)** |
| Food Donation Lifecycle | `tests/test_donations.py` | 5 | **PASS (100%)** |
| Rule-Based Smart Matching | `tests/test_matching.py` | 5 | **PASS (100%)** |
| Claim & Collection Lifecycle | `tests/test_claims.py` | 6 | **PASS (100%)** |
| Administration & Reporting | `tests/test_admin.py` | 4 | **PASS (100%)** |
| **Total** | | **26** | **26 / 26 PASSED** |

---

## 2. Test Case Specifications

### A. Authentication & Access Control (`test_auth.py`)

| Test ID | Test Name | Objective / Scenario | Expected Result | Actual Result |
|---|---|---|---|:---:|
| TC-AUTH-01 | `test_user_registration_donor` | Register new Food Donor with valid details | User record created with role=DONOR and verification_status=APPROVED | **PASSED** |
| TC-AUTH-02 | `test_user_registration_ngo_status_pending` | Register new NGO with organizational data | User created with role=NGO and verification_status=PENDING | **PASSED** |
| TC-AUTH-03 | `test_duplicate_email_registration_rejected` | Register with an existing email address | Request rejected with flash warning "already exists" | **PASSED** |
| TC-AUTH-04 | `test_login_success_and_role_redirect` | Log in with valid credentials for Donor, NGO, and Admin | Successful authentication and automatic redirect to role dashboard | **PASSED** |
| TC-AUTH-05 | `test_invalid_login_rejected` | Attempt login with invalid password | Authentication rejected with "Invalid email or password" | **PASSED** |
| TC-AUTH-06 | `test_role_access_boundaries` | Access Admin or NGO pages with a Donor session | Access blocked; redirected with permission flash warning | **PASSED** |

### B. Food Donation Management (`test_donations.py`)

| Test ID | Test Name | Objective / Scenario | Expected Result | Actual Result |
|---|---|---|---|:---:|
| TC-DON-01 | `test_create_donation_success` | Publish surplus food listing with valid future deadline | Listing created with status=AVAILABLE and stored in SQLite | **PASSED** |
| TC-DON-02 | `test_create_donation_invalid_quantity` | Publish listing with zero or negative quantity | Input rejected with ListingServiceError ("Quantity must be positive") | **PASSED** |
| TC-DON-03 | `test_create_donation_past_deadline_rejected` | Set collection deadline to past datetime | Input rejected with ListingServiceError ("deadline must be in future") | **PASSED** |
| TC-DON-04 | `test_edit_donation_unauthorized` | Attempt to modify a listing belonging to another donor | Unauthorized modification rejected with permission error | **PASSED** |
| TC-DON-05 | `test_cancel_donation` | Donor cancels active food listing | Listing transitioned to CANCELLED status | **PASSED** |

### C. Rule-Based Smart Matching Algorithm (`test_matching.py`)

| Test ID | Test Name | Objective / Scenario | Expected Result | Actual Result |
|---|---|---|---|:---:|
| TC-MAT-01 | `test_category_scoring` | Score exact match vs compatible category vs neutral | Exact=100.0, Compatible=75.0, Neutral=50.0 | **PASSED** |
| TC-MAT-02 | `test_location_scoring` | Score locality vs city vs district compatibility | Same Locality=100.0, Same City=80.0 | **PASSED** |
| TC-MAT-03 | `test_urgency_scoring` | Score collection deadline urgency windows | < 2 hrs=100.0, 2–6 hrs=85.0 | **PASSED** |
| TC-MAT-04 | `test_composite_formula_calculation` | Verify weighted formula: 40% Cat + 25% Loc + 20% Qty + 15% Urg | Composite score = 100 with label "Excellent Match" | **PASSED** |
| TC-MAT-05 | `test_ranking_and_expired_exclusion` | Rank available listings and verify expired exclusion | Expired listings excluded; highest match score ranked first | **PASSED** |

### D. Claim & Collection Lifecycle (`test_claims.py`)

| Test ID | Test Name | Objective / Scenario | Expected Result | Actual Result |
|---|---|---|---|:---:|
| TC-CLM-01 | `test_claim_submission_approved_ngo` | Approved NGO claims available donation | Listing -> RESERVED, Claim -> PENDING (Step 1) | **PASSED** |
| TC-CLM-02 | `test_claim_submission_unapproved_ngo_rejected` | Pending unapproved NGO attempts to claim | Claim rejected ("pending administrative verification") | **PASSED** |
| TC-CLM-03 | `test_duplicate_claim_prevention` | Attempt second claim on an already reserved listing | Transaction blocked ("not available for claiming") | **PASSED** |
| TC-CLM-04 | `test_full_collection_workflow_steps` | Execute 4-step pipeline: PENDING -> ACCEPTED -> READY -> COLLECTED | Statuses transition cleanly, step_numbers 1-4, collected_at recorded | **PASSED** |
| TC-CLM-05 | `test_reject_claim_releases_listing` | Donor declines claim | Claim -> REJECTED, Listing restored to AVAILABLE | **PASSED** |
| TC-CLM-06 | `test_cancel_claim_by_ngo_releases_listing` | NGO cancels pending claim | Claim -> CANCELLED, Listing restored to AVAILABLE | **PASSED** |

### E. Administrator Oversight (`test_admin.py`)

| Test ID | Test Name | Objective / Scenario | Expected Result | Actual Result |
|---|---|---|---|:---:|
| TC-ADM-01 | `test_admin_dashboard_statistics` | Verify genuine SQLite metrics count | Correct counts for total users, donors, NGOs, pending approvals | **PASSED** |
| TC-ADM-02 | `test_admin_ngo_approval` | Admin approves pending NGO account | Status becomes APPROVED; NGO can now claim donations | **PASSED** |
| TC-ADM-03 | `test_admin_ngo_rejection` | Admin rejects NGO account | Status becomes REJECTED; NGO cannot claim food | **PASSED** |
| TC-ADM-04 | `test_unauthorized_admin_access_blocked` | Regular users attempt access to /admin routes | Blocked; access denied | **PASSED** |

---

## 3. How to Run Tests

Run the full automated test suite locally:

```powershell
# Using the virtual environment
.venv\Scripts\python.exe -m pytest -v

# Or with system Python
python -m pytest -v
```
