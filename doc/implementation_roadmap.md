# 📘 IMPLEMENTATION ROADMAP

**Project:** Remedial Management System (RMS)
**Duration:** 120 Days
**Approach:** Phased, control-first implementation

---

# PHASE 1 — FOUNDATION & CONTROL DESIGN

**Timeline:** Weeks 1–4
**Objective:** Governance clarity before system build

---

## Week 1 – Project Mobilization

### 1️⃣ Create Project Steering Committee

* CEO / President (Sponsor)
* Credit Head
* Remedial Officer
* Compliance Officer
* IT Lead
* Internal Audit (Observer)

### 2️⃣ Approve:

* BRD
* ERD
* Data Dictionary
* Approval matrix thresholds

Deliverable:

* Signed Project Charter

---

## Week 2 – Policy Alignment

### Review & Amend:

* Credit Policy
* Remedial Policy
* Compromise Authority Limits
* Write-Off Policy

Must reflect:

* Approval levels
* Discount thresholds
* Rescission rule
* Legal trigger rule
* Write-off governance

Deliverable:

* Board-approved policy addendum

---

## Week 3 – Data Preparation

### Extract:

* All active loans
* All past due loans
* NPL portfolio
* Collateral list
* Legal case list
* Write-off history

### Clean:

* Duplicate borrowers
* Missing DPD data
* Incorrect classifications
* Exposure reconciliation issues

Deliverable:

* Clean NPL master file

---

## Week 4 – System Architecture Finalization

Confirm:

* Database engine (PostgreSQL recommended)
* Hosting (on-prem vs cloud)
* Backup protocol
* Access control structure

Deliverable:

* Technical Architecture Document

---

# PHASE 2 — CORE SYSTEM BUILD

**Timeline:** Weeks 5–8
**Objective:** Build Minimum Viable RMS

---

## Week 5 – Core Tables Deployment

Build:

* Borrower
* Loan Account
* Exposure Snapshot
* Delinquency Status
* Remedial Case

Test:

* Auto NPL tagging
* DPD computation
* Provision calculation

---

## Week 6 – Strategy & Collection Module

Build:

* Strategy Assignment
* Collection Activity Log
* Promise-to-Pay Tracker

Test:

* Broken PTP auto-flag
* Single active strategy rule

---

## Week 7 – Compromise & Approval Module

Build:

* Compromise Agreement
* Installment Schedule
* Approval Workflow
* Authority validation logic

Test:

* Discount > threshold auto-route
* Missed installment auto-rescind

---

## Week 8 – Legal & Write-Off Module

Build:

* Legal Case Tracker
* Foreclosure Monitoring
* Write-Off Table
* Recovery Table

Test:

* Write-off cannot proceed without approval record
* Post write-off recovery tracking

---

# PHASE 3 — REPORTING & DASHBOARD

**Timeline:** Weeks 9–10

Build dashboards:

1. NPL Ratio
2. Aging Summary
3. Top 20 Exposures
4. Compromise Discount Summary
5. Write-Off vs Recovery
6. Remedial Officer Performance
7. Foreclosure Pipeline

Board-level summary view required.

---

# PHASE 4 — PARALLEL RUN & CONTROL TESTING

**Timeline:** Weeks 11–12

---

## Week 11 – Parallel Run

* Run RMS alongside manual tracking
* Validate:

  * Exposure totals
  * NPL tagging
  * Provision accuracy
  * Strategy logs

Internal Audit performs test sampling.

---

## Week 12 – Control Validation

Test:

* Segregation of duties
* Approval enforcement
* Audit trail immutability
* DPD cannot be manually edited

Deliverable:

* Internal Audit sign-off memo

---

# PHASE 5 — GO LIVE

**Timeline:** Week 13

1. Freeze manual remedial tracker.
2. Declare RMS as official system of record.
3. Issue Management Circular.

---

# POST-IMPLEMENTATION (Month 4–6)

Enhancements:

* SMS reminder integration
* Collateral valuation alerts
* Insurance expiry alerts
* Automated board report generation
* Early warning system for watchlist accounts

---

# RESOURCE REQUIREMENTS

## Manpower

* 1 IT Developer (full-time)
* 1 Remedial Officer (SME)
* 1 Credit Officer
* 1 Compliance Reviewer
* 1 Internal Audit Reviewer

---

# KEY IMPLEMENTATION RISKS

| Risk                     | Mitigation                    |
| ------------------------ | ----------------------------- |
| Data quality issues      | Clean data before migration   |
| Resistance from staff    | Conduct training              |
| Governance bypass        | Hard-code approval validation |
| Incomplete documentation | Mandatory field validation    |
| IT overload              | Phased build                  |

---

# SUCCESS CRITERIA (6 Months After Go Live)

* 100% NPLs in RMS
* 100% compromises digitally approved
* 100% write-offs documented
* 0 unresolved audit issues
* Measurable NPL ratio reduction

