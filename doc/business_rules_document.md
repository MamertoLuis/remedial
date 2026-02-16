# 📘 BUSINESS REQUIREMENTS DOCUMENT (BRD)

**Project:** Remedial Management System (RMS)
**Institution:** Upland Rural Bank of Dalaguete, Cebu Inc.
**Prepared By:** Credit & Risk Management
**Version:** 1.0

---

# 1. PROJECT OBJECTIVE

To design and implement a centralized Remedial Management System that:

1. Tracks all past due and non-performing loans (NPLs)
2. Automates delinquency classification
3. Controls compromise and restructuring approvals
4. Logs all collection and legal actions
5. Ensures BSP regulatory compliance
6. Strengthens governance and audit trail integrity

---

# 2. BUSINESS DRIVERS

The RMS must support:

* Reduction of NPL ratio
* Strengthened internal controls
* Clear approval hierarchy
* Accurate provisioning computation
* Clean audit trail for BSP examination
* Board-level visibility of remedial exposure

---

# 3. SCOPE

## Included

* Past due monitoring
* NPL tagging
* Remedial case management
* Collection tracking
* Compromise management
* Legal case tracking
* Write-off management
* Recovery monitoring
* Approval workflows
* Dashboard reporting

## Excluded (Phase 1)

* Core banking booking
* Automated SMS integration
* External legal firm portal

---

# 4. STAKEHOLDERS

| Role               | Responsibility                          |
| ------------------ | --------------------------------------- |
| Board of Directors | Approves major write-offs & compromises |
| Credit Committee   | Reviews remedial strategies             |
| Branch Manager     | Collection oversight                    |
| Remedial Officer   | Case management                         |
| Compliance Officer | Regulatory alignment                    |
| Internal Audit     | Control testing                         |
| IT Unit            | System maintenance                      |

---

# 5. HIGH-LEVEL BUSINESS PROCESS FLOW

```
Performing Loan
      ↓
Past Due
      ↓
NPL Classification (≥ 90 DPD)
      ↓
Remedial Case Creation
      ↓
Strategy Assignment
      ↓
    (Choose Path)
Collection | Restructure | Compromise | Legal | Foreclosure
      ↓
Write-off (if Loss)
      ↓
Recovery Monitoring
```

---

# 6. FUNCTIONAL REQUIREMENTS

---

## 6.1 Delinquency Monitoring Module

### FR-01: Automatic DPD Calculation

* System shall compute Days Past Due daily.
* IF DPD ≥ 90 → Auto-tag NPL.

### FR-02: Classification Mapping

* System shall assign:

  * SM
  * Substandard
  * Doubtful
  * Loss
* Based on aging thresholds.

### FR-03: Provisioning Calculation

* Provision % auto-applied based on classification.
* Exposure must reconcile with accounting GL.

---

## 6.2 Remedial Case Management

### FR-04: Automatic Case Creation

* When NPL flag = TRUE
* System auto-creates Remedial Case.

### FR-05: Single Active Case Rule

* Each loan can only have one active remedial case.

### FR-06: Stage Management

System must track case stage:

* COLLECTION
* RESTRUCTURE
* COMPROMISE
* LEGAL
* FORECLOSURE
* WRITEOFF
* RECOVERY
* CLOSED

---

## 6.3 Collection Management

### FR-07: Activity Logging

System must log:

* Calls
* Visits
* Demand letters
* Negotiations
* SMS reminders

Each log must include:

* Date
* Staff
* Remarks
* Next action date

### FR-08: Promise-to-Pay Monitoring

* Track promised amount
* Track promised date
* Auto-flag broken promises

---

## 6.4 Compromise Management

### FR-09: Compromise Proposal Encoding

System must capture:

* Original exposure
* Proposed compromise amount
* Discount amount
* Discount percentage

### FR-10: Approval Workflow

IF:

* Discount ≤ 10% → Branch Manager
* Discount > 10% → Credit Committee
* Discount > 20% → Board Approval

(Threshold configurable.)

### FR-11: Installment Monitoring

* Generate compromise schedule
* Auto-flag missed installment
* Trigger rescission rule if overdue beyond grace period

### FR-12: Rescission Rule

IF installment overdue > grace days:

* Compromise status = RESCINDED
* Original exposure reinstated
* Legal path enabled

---

## 6.5 Legal & Foreclosure Module

### FR-13: Legal Case Tracking

* Capture filing date
* Court
* Docket number
* Case status

### FR-14: Foreclosure Monitoring

* Capture auction date
* Redemption expiry
* Property acquisition status

---

## 6.6 Write-Off & Recovery

### FR-15: Write-Off Control

* Cannot write off without approval record.
* Must record Board Resolution reference.

### FR-16: Recovery After Write-Off

* Record post write-off collections.
* System must not revive written-off loan as performing.

---

## 6.7 Governance & Approval

### FR-17: Configurable Approval Matrix

System must support:

* Multi-level approval steps
* Digital timestamp logging
* Decision notes

### FR-18: Immutable Audit Trail

System must log:

* Status changes
* Exposure changes
* Discount approvals
* Write-offs

Logs must not be editable.

---

# 7. NON-FUNCTIONAL REQUIREMENTS

---

## 7.1 Security

* Role-based access control
* Segregation of duties
* Approval authority enforced
* Two-factor authentication (Phase 2)

---

## 7.2 Performance

* Load NPL portfolio ≤ 5 seconds
* Dashboard refresh ≤ 10 seconds
* Support at least 10 concurrent users

---

## 7.3 Data Integrity

* Referential integrity enforced
* Exposure must reconcile with core banking
* Daily backup
* Monthly archive

---

## 7.4 Compliance Alignment

System must support compliance with:

* Loan classification and provisioning rules
* Credit exposure monitoring standards under BSP Circular No. 1150 
* Financial Consumer Protection logging requirements under BSP Circular No. 1160 
* Capital adequacy computation linkage 

---

# 8. REPORTING REQUIREMENTS

System must generate:

1. NPL Ratio
2. Aging Summary
3. Top 20 Exposures
4. Compromise Discount Report
5. Write-Off Summary
6. Recovery Performance
7. Foreclosure Pipeline
8. Provision Coverage Ratio
9. Remedial Performance by Officer
10. Board Dashboard Summary

---

# 9. CONTROL REQUIREMENTS

1. No compromise approval without authority level validation.
2. No write-off without Board approval log.
3. No loan may return to Performing without compliance review.
4. DPD auto-calculated and cannot be manually overridden.
5. All status transitions logged.

---

# 10. RISKS IF SYSTEM NOT IMPLEMENTED

* Manual tracking errors
* BSP examination findings
* Inconsistent provisioning
* Governance weaknesses
* Fraud risk in compromise approvals
* Lack of portfolio visibility

---

# 11. SUCCESS METRICS

* 100% of NPLs recorded in RMS
* 100% of compromises digitally approved
* 100% of write-offs documented with approval reference
* Reduction in NPL ratio within 12 months
