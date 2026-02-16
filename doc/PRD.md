# I. SYSTEM DOMAIN ARCHITECTURE

Your MIS should have these primary domains:

```
Remedial Management System (RMS)
│
├── 1. Account Master Domain
├── 2. Exposure & Financial Domain
├── 3. Delinquency & Classification Domain
├── 4. Collection Activity Domain
├── 5. Remedial Action Domain
├── 6. Compromise & Restructuring Domain
├── 7. Legal & Foreclosure Domain
├── 8. Collateral Domain
├── 9. Write-Off & Recovery Domain
├── 10. Governance & Approval Domain
├── 11. Regulatory Reporting Domain
```

---

# II. DATA DICTIONARY (Core Entities)

Below are the **essential tables/entities** you must define.

---

## 1️⃣ Account Master Table

**Primary Key:** Account_ID

Fields:

* Account_ID
* Borrower_ID
* Borrower_Name
* Loan_Type
* Booking_Date
* Original_Principal
* Interest_Rate
* Maturity_Date
* Branch_Code
* Account_Officer
* Security_Type (Unsecured / REM / CM / Mixed)
* Current_Status (Performing / Past Due / NPL / Written-Off)
* Days_Past_Due
* NPL_Date

---

## 2️⃣ Exposure Table

* Account_ID (FK)
* Principal_Outstanding
* Accrued_Interest
* Accrued_Penalty
* Legal_Fees
* Other_Charges
* Total_Exposure
* Provision_Level
* Provision_Amount
* Last_Computed_Date

---

## 3️⃣ Delinquency & Classification Table

* Account_ID
* Past_Due_Start_Date
* Aging_Bucket (30 / 60 / 90 / 180 / 360+)
* Classification (Especially Mentioned / Substandard / Doubtful / Loss)
* NPL_Flag
* Date_Classified
* Next_Review_Date

Must align with BSP loan classification rules.

---

## 4️⃣ Collection Activity Log

Every action must be logged.

* Activity_ID
* Account_ID
* Activity_Date
* Activity_Type (Call / Visit / Demand Letter / Negotiation)
* Remarks
* Promise_To_Pay_Amount
* Promise_To_Pay_Date
* Staff_Assigned
* Next_Action_Date

Critical for audit and legal defensibility.

---

## 5️⃣ Remedial Strategy Table

This determines account treatment:

* Account_ID
* Strategy_Type

  * Intensive Collection
  * Restructuring
  * Compromise
  * Foreclosure
  * Legal Action
  * Write-Off
* Strategy_Start_Date
* Strategy_Status
* Strategy_Outcome

---

## 6️⃣ Compromise Module Table

If account enters compromise domain:

* Compromise_ID
* Account_ID
* Original_Total_Exposure
* Approved_Compromise_Amount
* Discount_Amount
* Discount_Percentage
* Approval_Level (AO / Manager / Board)
* Approval_Date
* Installment_Flag
* Rescission_Clause_Flag
* Compromise_Status (Active / Completed / Rescinded)

If installment:

* Installment_Number
* Due_Date
* Amount_Due
* Amount_Paid
* Payment_Date
* Status

---

## 7️⃣ Collateral Table

* Collateral_ID
* Account_ID
* Type (REM / CM / Deposit Holdout)
* Location
* TCT_Number
* Appraised_Value
* Last_Appraisal_Date
* Forced_Sale_Value
* Insurance_Expiry
* Foreclosure_Status

---

## 8️⃣ Legal Domain Table

* Case_ID
* Account_ID
* Case_Type (Judicial / Extra-judicial)
* Filing_Date
* Court_Name
* Docket_Number
* Case_Status
* Hearing_Date
* Redemption_Period_End

---

## 9️⃣ Write-Off Table

* Writeoff_ID
* Account_ID
* Board_Approval_Date
* Writeoff_Amount
* Reason
* Recovery_After_Writeoff (Y/N)

---

## 10️⃣ Governance & Approval Table

* Approval_ID
* Account_ID
* Action_Type
* Requested_By
* Approved_By
* Approval_Level
* Approval_Date
* Board_Resolution_Number

Critical for audit and BSP exam.

---

# III. BUSINESS RULES (This is where most banks fail)

Now the important part.

---

## 1️⃣ NPL Rule

IF Days_Past_Due ≥ 90
THEN:

* NPL_Flag = TRUE
* Account moves to Remedial Domain
* Provision recalculated
* AO access limited
* Remedial Officer assigned

---

## 2️⃣ Strategy Assignment Rule

IF Exposure > ₱500,000
THEN Strategy must be approved by Credit Committee.

IF Discount > 20%
THEN Board Approval Required.

---

## 3️⃣ Compromise Rescission Rule

IF Installment_Missed = TRUE
AND Grace_Period_Expired
THEN:

* Compromise_Status = Rescinded
* Original_Exposure_Reinstated
* Legal_Action_Eligible = TRUE

---

## 4️⃣ Foreclosure Trigger Rule

IF NPL_Days ≥ 180
AND No Viable Payment
THEN Flag for foreclosure evaluation.

---

## 5️⃣ Write-Off Rule

IF Classified as Loss
AND No Payment ≥ 12 months
AND Collection Exhausted
THEN Eligible for Board Write-Off.

---

## 6️⃣ Provisioning Link Rule

Provision amount auto-updates based on classification.

Must align with capital rules under BSP capital adequacy framework 

---

## 7️⃣ Consumer Protection Rule

All borrower communication logged (BSP FCP compliance) 

---

# IV. WORKFLOW STATES (Very Important for MIS)

Each account should have only one main status at a time:

```
Performing
→ Past Due
→ NPL
→ Remedial Strategy Assigned
    → Restructuring
    → Compromise
    → Legal
    → Foreclosure
→ Write-Off
→ Recovery
```

No skipping without approval log.

---

# V. REPORTING OUTPUTS (Board Level)

Your MIS must generate:

1. NPL Ratio by branch
2. Aging Summary
3. Top 20 Exposures
4. Compromise Discounts Granted
5. Write-offs vs Recoveries
6. Foreclosure Pipeline
7. Provision Coverage Ratio
8. Remedial Performance by Officer

---


