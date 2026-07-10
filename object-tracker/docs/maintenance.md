# Maintenance Strategy — Trackr v1.0

To ensure Trackr's long-term sustainability, reliability, and security, this maintenance plan defines the release cadence, bug triage processes, and lifecycle support policies.

---

## 1. Version Support Policy

Trackr follows **Semantic Versioning (SemVer)**: `MAJOR.MINOR.PATCH`.

* **MAJOR**: Backward-incompatible API changes or major architectural redesigns.
* **MINOR**: New features added in a backward-compatible manner (e.g. adding a new tracker plugin).
* **PATCH**: Backward-compatible bug fixes, security patches, or documentation improvements.

### 1.1 Support Windows
We support two release streams:
* **Active Support (v1.x)**: Receives features, performance improvements, and critical security fixes.
* **Security Only Support (v0.x)**: Receives critical security vulnerability patches only. No new features.

---

## 2. Bug Triage & Issue Prioritization

All reported issues are triaged by the maintainer team weekly. We categorize issues using the following priority matrix:

| Priority Level | Response SLA | Target Fix | Definition |
| :--- | :--- | :--- | :--- |
| **P0 - Critical** | < 12 Hours | Next Patch Release | Remote Code Execution (RCE), token leaks, database corruption, or system-wide crash. |
| **P1 - High** | < 48 Hours | Next Minor/Patch | Core feature broken (e.g. video fails to upload, tracking fails to link IDs). |
| **P2 - Medium** | < 1 Week | Scheduled Release | Non-critical bug or minor UI display glitch. |
| **P3 - Low** | < 2 Weeks | Backlog | Minor documentation correction or enhancement request. |

---

## 3. Deprecation Policy

When a feature or configuration setting is scheduled for removal:
1. **Deprecation Phase**: Mark the feature as deprecated in the codebase (emitting `DeprecationWarning`) and declare it in the Release Notes. It remains functional.
2. **Grace Period**: Deprecated features remain functional for at least one minor release cycle.
3. **Removal Phase**: The feature is permanently removed in the next Major version release.

---

## 4. Security Vulnerability Disclosure

If you discover a security vulnerability:
* **Do not open a public issue.**
* Send a detailed report to `security@trackr.io` with steps to reproduce and proof-of-concept.
* The maintainers will respond within 24 hours to coordinate a private fix.
* Once patched, a CVE is filed and credit is published in the release notes.
