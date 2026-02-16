# 📘 USER ACCESS MATRIX

**System:** Remedial Management System (RMS)
**Institution:** Upland Rural Bank of Dalaguete, Cebu Inc.
**Version:** 1.0

---

# 1️⃣ ROLE DEFINITIONS

| Role Code | Role Name            |
| --------- | -------------------- |
| AO        | Account Officer      |
| RO        | Remedial Officer     |
| BM        | Branch Manager       |
| CC        | Credit Committee     |
| BOD       | Board of Directors   |
| CO        | Compliance Officer   |
| IA        | Internal Audit       |
| IT        | System Administrator |
| FIN       | Finance/Accounting   |

---

# 2️⃣ ACCESS LEVEL DEFINITIONS

| Level | Description         |
| ----- | ------------------- |
| V     | View Only           |
| E     | Encode              |
| M     | Modify              |
| A     | Approve             |
| D     | Delete (restricted) |
| X     | No Access           |

Delete rights should be disabled in production for most roles.

---

# 3️⃣ MODULE ACCESS MATRIX

## A. Borrower & Loan Master

| Role | View | Encode | Modify | Approve |
| ---- | ---- | ------ | ------ | ------- |
| AO   | V    | X      | X      | X       |
| RO   | V    | X      | X      | X       |
| BM   | V    | X      | X      | X       |
| CC   | V    | X      | X      | X       |
| BOD  | V    | X      | X      | X       |
| CO   | V    | X      | X      | X       |
| IA   | V    | X      | X      | X       |
| IT   | V    | E      | M      | X       |
| FIN  | V    | X      | X      | X       |

Control Rule:
Loan booking must remain in Core Banking, not RMS.

---

## B. Delinquency & Exposure Module

| Role | View | Modify | Approve |
| ---- | ---- | ------ | ------- |
| AO   | V    | X      | X       |
| RO   | V    | X      | X       |
| BM   | V    | X      | X       |
| CC   | V    | X      | X       |
| BOD  | V    | X      | X       |
| CO   | V    | X      | X       |
| IA   | V    | X      | X       |
| IT   | V    | X      | X       |
| FIN  | V    | X      | X       |

Control Rule:
DPD and Exposure are auto-calculated.
No user override allowed.

---

## C. Remedial Case Management

| Role | View | Encode | Modify | Approve       |
| ---- | ---- | ------ | ------ | ------------- |
| AO   | V    | X      | X      | X             |
| RO   | V    | E      | M      | X             |
| BM   | V    | E      | M      | A (low level) |
| CC   | V    | X      | X      | A             |
| BOD  | V    | X      | X      | A             |
| CO   | V    | X      | X      | X             |
| IA   | V    | X      | X      | X             |
| IT   | V    | X      | X      | X             |

Control Rule:
Only RO can create or update remedial case.
BM may approve minor strategy shifts.

---

## D. Collection Activity Module

| Role | View | Encode | Modify               |
| ---- | ---- | ------ | -------------------- |
| AO   | V    | E      | M (own entries only) |
| RO   | V    | E      | M                    |
| BM   | V    | X      | X                    |
| CC   | V    | X      | X                    |
| BOD  | V    | X      | X                    |
| CO   | V    | X      | X                    |
| IA   | V    | X      | X                    |
| IT   | V    | X      | X                    |

Control Rule:
AO can log activity but cannot change case stage.

---

## E. Compromise Module

| Role | View | Encode | Modify | Approve    |
| ---- | ---- | ------ | ------ | ---------- |
| AO   | V    | X      | X      | X          |
| RO   | V    | E      | M      | X          |
| BM   | V    | X      | X      | A (≤10%)   |
| CC   | V    | X      | X      | A (10–20%) |
| BOD  | V    | X      | X      | A (>20%)   |
| CO   | V    | X      | X      | X          |
| IA   | V    | X      | X      | X          |
| IT   | V    | X      | X      | X          |

Control Rule:
System must auto-route based on discount % threshold.

---

## F. Legal Module

| Role | View | Encode | Modify |
| ---- | ---- | ------ | ------ |
| RO   | V    | E      | M      |
| BM   | V    | X      | X      |
| CC   | V    | X      | X      |
| BOD  | V    | X      | X      |
| CO   | V    | X      | X      |
| IA   | V    | X      | X      |

Only Remedial Officer updates legal status.

---

## G. Write-Off Module

| Role | View | Encode | Approve   |
| ---- | ---- | ------ | --------- |
| RO   | V    | E      | X         |
| BM   | V    | X      | X         |
| CC   | V    | X      | Recommend |
| BOD  | V    | X      | A         |
| FIN  | V    | X      | X         |
| IA   | V    | X      | X         |

Control Rule:
Write-off requires:

* Board Approval record
* Resolution number
* Cannot be encoded as approved without BOD digital sign-off.

---

## H. Recovery After Write-Off

| Role | View | Encode |
| ---- | ---- | ------ |
| RO   | V    | E      |
| FIN  | V    | E      |
| IA   | V    | X      |

---

## I. Approval Workflow Module

| Role | View | Approve          |
| ---- | ---- | ---------------- |
| BM   | V    | A (within limit) |
| CC   | V    | A                |
| BOD  | V    | A                |
| IA   | V    | X                |
| CO   | V    | X                |

Approval logs must be immutable.

---

# 4️⃣ SEGREGATION OF DUTIES CONTROLS

The following combinations are STRICTLY PROHIBITED:

1. Same user cannot:

   * Propose compromise AND approve it.
2. Same user cannot:

   * Encode write-off AND mark it approved.
3. IT Administrator cannot:

   * Approve any credit action.
4. Remedial Officer cannot:

   * Override DPD or exposure.

---

# 5️⃣ SPECIAL SYSTEM CONTROLS

* Approval rights based on role, not name.
* Multi-factor authentication for BOD approvals (Phase 2).
* All approval timestamps stored.
* No delete rights in production (soft delete only).

---

# 6️⃣ INTERNAL AUDIT ACCESS

Internal Audit shall have:

* View access to all modules
* Access to audit logs
* Access to historical status transitions
* Access to approval workflow trail
* Access to write-off history

No editing capability.

---

# 7️⃣ GOVERNANCE ENFORCEMENT RULES

1. Role-based access must be assigned by Compliance.
2. IT cannot assign itself approval rights.
3. Quarterly user access review required.
4. Dormant user accounts auto-deactivated after 60 days.
5. All privileged access changes logged.

---

# CONTROL OBJECTIVE

This matrix ensures:

* No single-point override of credit decisions
* Controlled compromise authority
* Proper board oversight
* Regulatory defensibility
* Fraud risk mitigation
