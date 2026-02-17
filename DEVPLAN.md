# Development Plan

## Phase 1: MVP

### Domain: Account Master

- [x] Setup Django project
- [x] Define `LoanAccount` and `Borrower` models
- [x] Create views for listing and detailing accounts and borrowers
- [x] Implement `django-tables2` for list views
- [x] Fix "Add New" links in `AccountDetails`
- [x] Fix decimal number formatting to show commas
- [x] Consolidate dummy data loading scripts

### Domain: Compromise Agreement

- [x] Create `compromise_agreement` app
- [x] Define `CompromiseAgreement` and `CompromiseInstallment` models
- [x] Create forms for `CompromiseAgreement` and `CompromiseInstallment`
- [x] Create `django-tables2` tables for `CompromiseAgreement` and `CompromiseInstallment`
- [x] Create views for `CompromiseAgreement` CRUD operations
- [x] Create templates for `CompromiseAgreement` views
- [x] Add URLs for `compromise_agreement` app
- [x] Add link to compromise agreement list in navigation

### Next Steps

- [ ] Add link to compromise agreement list page in the base template or dashboard.
- [ ] Thoroughly test the new compromise agreement functionality.
- [x] Create views for `CompromiseInstallment` CRUD operations (Creation and Update views already exist and are working. Listing is handled by `CompromiseAgreementDetailView`).
- [x] Create templates for `CompromiseInstallment` views (Form template already exists. Listing is handled by `CompromiseAgreementDetailView`).

---

## Development Guidelines

### Data Import Workflow

- **Core Banking System (CBS) Data Import:** Data from the CBS, including raw financial figures necessary for calculating DPD (Days Past Due) and Exposure, will be imported into the RMS via a **manual monthly CSV upload**. This process will *not* be automated via cron jobs or CBS APIs. The RMS will then perform its auto-calculations based on this imported data.

### Testing Principles

- **Avoid Brittle Assertions for Formatted Strings:** When writing functional tests that check rendered HTML (e.g., using `assertContains`), avoid asserting against complete, locale-sensitive formatted strings like dates or numbers with thousand separators. These tests can be brittle and fail due to subtle, non-visible formatting differences between the test environment and the template rendering engine.
  - **Instead:** Assert against the individual, unformatted components of the data or static parts of the rendered string.
  - **Example:** Instead of `self.assertContains(response, 'Feb 07, 2026')`, it is more robust to use separate assertions like `self.assertContains(response, 'Feb')`, `self.assertContains(response, '7')`, and `self.assertContains(response, '2026')`.
