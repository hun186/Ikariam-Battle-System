# Known Issues

## Open Issues
| ID | Severity | Issue | Impact | Workaround/evidence | Status |
| --- | --- | --- | --- | --- | --- |
| KI-001 | High | Current official unit stats/rules could not be verified; network access to GitHub returned HTTP 403 and web lookup was unavailable. | `paper-2020` cannot represent current-game accuracy. | Registry and UI explicitly version/label the PDF subset; reject unsupported ids. | Open |
| KI-002 | High | PDF does not supply an a-priori kill-type selector, general rounding, SR/IR triggers, or retargeting. | Strict simulations stop inconclusive before casualties. | Use strict for evidence-safe output; experimental results disclose `EXP-I-KILL-001`. | Mitigated |
