# 📘 DATA DICTIONARY DOCUMENT

**System:** Remedial Management System (RMS)
**Institution:** Upland Rural Bank of Dalaguete, Cebu Inc.
**Version:** 1.0
**Owner:** Credit & Remedial Unit

---

# 1️⃣ BORROWER TABLE

**Table Name:** `borrower`
**Primary Key:** `borrower_id`

| Field Name           | Data Type | Length | Nullable | Description                | Validation Rules                  |
| -------------------- | --------- | ------ | -------- | -------------------------- | --------------------------------- |
| borrower_id          | VARCHAR   | 20     | No       | Unique borrower identifier | System-generated                  |
| borrower_type        | ENUM      | -      | No       | PERSON / CORP / COOP       | Must match legal classification   |
| full_name            | VARCHAR   | 200    | No       | Complete legal name        | No special characters except ., - |
| tin                  | VARCHAR   | 20     | Yes      | Tax Identification Number  | Numeric format check              |
| birth_or_incorp_date | DATE      | -      | Yes      | DOB or Incorporation Date  | Cannot be future date             |
| primary_address      | VARCHAR   | 300    | No       | Registered address         | Required                          |
| mobile               | VARCHAR   | 20     | Yes      | Contact number             | Format validation                 |
| email                | VARCHAR   | 150    | Yes      | Email address              | Valid email format                |
| risk_rating          | VARCHAR   | 10     | Yes      | Internal risk grade        | Based on credit policy            |

---

# 2️⃣ LOAN ACCOUNT TABLE

**Table Name:** `loan_account`
**Primary Key:** `loan_id`
**Foreign Key:** `borrower_id`

| Field Name         | Data Type | Length | Nullable | Description                                     | Validation Rules             |
| ------------------ | --------- | ------ | -------- | ----------------------------------------------- | ---------------------------- |
| loan_id            | VARCHAR   | 20     | No       | Unique loan reference                           | System-generated             |
| borrower_id        | VARCHAR   | 20     | No       | Linked borrower                                 | Must exist in borrower table |
| pn_number          | VARCHAR   | 50     | No       | Promissory Note number                          | Unique                       |
| booking_date       | DATE      | -      | No       | Loan booking date                               | Cannot exceed current date   |
| maturity_date      | DATE      | -      | No       | Loan maturity                                   | Must be > booking_date       |
| original_principal | DECIMAL   | 15,2   | No       | Original loan amount                            | > 0                          |
| interest_rate      | DECIMAL   | 5,2    | No       | Annual rate (%)                                 | 0–100                        |
| loan_type          | VARCHAR   | 50     | No       | Agri / SME / Consumer                           | Predefined list              |
| branch_code        | VARCHAR   | 10     | No       | Branch identifier                               | Must match branch master     |
| account_officer_id | VARCHAR   | 20     | Yes      | Responsible AO                                  | Must exist in employee table |
| status             | ENUM      | -      | No       | PERFORMING / PAST_DUE / NPL / WRITEOFF / CLOSED | Auto-updated by system       |

---

# 3️⃣ EXPOSURE SNAPSHOT TABLE

**Table Name:** `exposure_snapshot`
**Primary Key:** `snapshot_id`
**Foreign Key:** `loan_id`

| Field Name            | Data Type     | Description           | Rules                        |
| --------------------- | ------------- | --------------------- | ---------------------------- |
| snapshot_id           | VARCHAR(20)   | Unique snapshot ID    | System-generated             |
| loan_id               | VARCHAR(20)   | Linked loan           | Required                     |
| as_of_date            | DATE          | Reporting date        | Required                     |
| principal_outstanding | DECIMAL(15,2) | Outstanding principal | ≥ 0                          |
| accrued_interest      | DECIMAL(15,2) | Accrued interest      | ≥ 0                          |
| accrued_penalty       | DECIMAL(15,2) | Penalties             | ≥ 0                          |
| legal_fees            | DECIMAL(15,2) | Legal charges         | ≥ 0                          |
| other_charges         | DECIMAL(15,2) | Misc charges          | ≥ 0                          |
| total_exposure        | DECIMAL(15,2) | System computed       | Must equal sum of components |
| provision_amount      | DECIMAL(15,2) | Required allowance    | Based on classification      |

---

# 4️⃣ DELINQUENCY STATUS TABLE

**Table Name:** `delinquency_status`

| Field Name     | Data Type   | Description               | Rules                     |
| -------------- | ----------- | ------------------------- | ------------------------- |
| delinquency_id | VARCHAR(20) | Unique ID                 | System-generated          |
| loan_id        | VARCHAR(20) | Linked loan               | Required                  |
| as_of_date     | DATE        | Classification date       | Required                  |
| days_past_due  | INT         | Days overdue              | ≥ 0                       |
| aging_bucket   | ENUM        | 30 / 60 / 90 / 180 / 360+ | Auto-derived              |
| classification | ENUM        | SM / SS / D / L           | Based on BSP standards    |
| npl_flag       | BOOLEAN     | True if ≥90 DPD           | Auto-trigger              |
| npl_date       | DATE        | Date became NPL           | Required if npl_flag=TRUE |

---

# 5️⃣ REMEDIAL CASE TABLE

**Table Name:** `remedial_case`

| Field          | Type        | Description                                                                                | Rules            |
| -------------- | ----------- | ------------------------------------------------------------------------------------------ | ---------------- |
| case_id        | VARCHAR(20) | Unique case ID                                                                             | System-generated |
| loan_id        | VARCHAR(20) | Linked loan                                                                                | Unique (1:1)     |
| case_open_date | DATE        | Date transferred to remedial                                                               | Auto if NPL      |
| case_owner_id  | VARCHAR(20) | Remedial officer                                                                           | Required         |
| case_stage     | ENUM        | COLLECTION / RESTRUCTURE / COMPROMISE / LEGAL / FORECLOSURE / WRITEOFF / RECOVERY / CLOSED | Only one active  |

---

# 6️⃣ COMPROMISE AGREEMENT TABLE

**Table Name:** `compromise_agreement`

| Field             | Type          | Description                    | Rules             |
| ----------------- | ------------- | ------------------------------ | ----------------- |
| compromise_id     | VARCHAR(20)   | Unique ID                      | System-generated  |
| case_id           | VARCHAR(20)   | Linked case                    | Unique            |
| approval_date     | DATE          | Date approved                  | Required          |
| original_exposure | DECIMAL(15,2) | Total before discount          | Required          |
| compromise_amount | DECIMAL(15,2) | Settlement amount              | > 0               |
| discount_amount   | DECIMAL(15,2) | Waived portion                 | System-calculated |
| discount_pct      | DECIMAL(5,2)  | Discount %                     | Auto-calculated   |
| installment_flag  | BOOLEAN       | Installment?                   | Required          |
| grace_days        | INT           | Grace period                   | ≥ 0               |
| status            | ENUM          | ACTIVE / COMPLETED / RESCINDED | Auto-updated      |

---

# 7️⃣ COMPROMISE SCHEDULE TABLE

| Field          | Type          | Description                   |
| -------------- | ------------- | ----------------------------- |
| sched_id       | VARCHAR(20)   | Unique ID                     |
| compromise_id  | VARCHAR(20)   | Linked compromise             |
| installment_no | INT           | Sequence                      |
| due_date       | DATE          | Payment date                  |
| amount_due     | DECIMAL(15,2) | Installment amount            |
| amount_paid    | DECIMAL(15,2) | Paid amount                   |
| paid_date      | DATE          | Actual payment                |
| status         | ENUM          | DUE / PAID / LATE / DEFAULTED |

---

# 8️⃣ LEGAL CASE TABLE

| Field           | Type         | Description                                      |
| --------------- | ------------ | ------------------------------------------------ |
| legal_id        | VARCHAR(20)  | Unique ID                                        |
| case_id         | VARCHAR(20)  | Linked remedial case                             |
| case_type       | ENUM         | JUDICIAL / EXTRAJUDICIAL / SMALLCLAIMS           |
| filing_date     | DATE         | Date filed                                       |
| court_or_office | VARCHAR(150) | Court name                                       |
| docket_no       | VARCHAR(50)  | Case number                                      |
| status          | ENUM         | FILED / ONGOING / JUDGMENT / SETTLED / DISMISSED |

---

# 9️⃣ WRITEOFF TABLE

| Field               | Type          | Description        |
| ------------------- | ------------- | ------------------ |
| writeoff_id         | VARCHAR(20)   | Unique ID          |
| case_id             | VARCHAR(20)   | Linked case        |
| board_approval_date | DATE          | Required           |
| writeoff_amount     | DECIMAL(15,2) | Amount written off |
| reason              | TEXT          | Narrative          |
| status              | ENUM          | WRITTEN_OFF        |

---

# 🔟 APPROVAL TABLE

| Field          | Type        | Description                                             |
| -------------- | ----------- | ------------------------------------------------------- |
| approval_id    | VARCHAR(20) | Unique ID                                               |
| case_id        | VARCHAR(20) | Linked case                                             |
| action_type    | ENUM        | COMPROMISE / RESTRUCTURE / FORECLOSE / WRITEOFF / LEGAL |
| requested_date | DATE        | Date requested                                          |
| requested_by   | VARCHAR(20) | Staff ID                                                |
| status         | ENUM        | PENDING / APPROVED / REJECTED                           |

---

# SYSTEM-WIDE VALIDATION RULES

1. A loan cannot enter `WRITEOFF` stage without approval record.
2. Compromise cannot be ACTIVE if status = RESCINDED.
3. Only one ACTIVE strategy per remedial case.
4. Exposure total must reconcile with GL.
5. DPD ≥ 90 → Auto-set NPL_FLAG = TRUE.
6. No payment accepted after writeoff unless Recovery module active.

---

# Audit Requirements

All tables must include:

* created_at (TIMESTAMP)
* created_by (USER ID)
* updated_at (TIMESTAMP)
* updated_by (USER ID)

Immutable logs required for:

* Status changes
* Approval decisions
* Compromise rescission
* Write-off posting

---

