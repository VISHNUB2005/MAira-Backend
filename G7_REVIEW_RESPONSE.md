# Group 7: response to the Technical Review & Remediation Brief

Status key: **Fixed + tested** = code changed and covered by an automated test (run `python -m pytest -v` and attach
your own output). **YOU MUST DO** = needs evidence only your team can produce. Do not tick a box without running it.

## 2. Findings
| Priority | Finding | Resolution | Test evidence |
|---|---|---|---|
| P0 Sender identity | Hardcoded personal From | No sender in code. `EMAIL_FROM_ADDRESS` is required for SMTP, validated, startup fails if missing/invalid. | `test_missing_smtp_setting_is_reported_by_name[EMAIL_FROM_ADDRESS]`, `test_invalid_sender_format_rejected`, `test_smtp_message_uses_configured_sender_and_own_message_id` |
| P0 Config validation | Swallowed `validate()` errors | No broad except. Validation runs when settings load and raises with a list of problems. | `test_valid_smtp_config_passes`, all config tests |
| P0 Fake provider success | SES/SendGrid simulated accepted=True | SES/SendGrid removed and rejected explicitly. Only SMTP is real. Dev/test providers are flagged `simulated=True`. | `test_unsupported_providers_are_rejected_explicitly`, `test_simulated_flag_and_semantics` |
| P0 OTP leakage | OTP inside ValueError | Generic `EmailValidationError` messages; OTP/address never in exceptions, logs, traces or results. | `test_invalid_input_errors_do_not_echo_otp_or_address`, `test_result_never_contains_the_otp`, `test_delivery_error_carries_only_a_sanitized_code`, failure tests in `test_group7_smtp_integration.py` |
| P1 Secret defaults | Default SMTP/JWT secrets | No default host, credentials or JWT key. JWT key must be provided and not a placeholder. | `test_no_default_smtp_host_or_credentials`, `test_no_default_jwt_key` |
| P1 Credential checks | None vs empty, wrong message | Each variable checked separately: "not set" vs "set but empty", correct name, no values. | `test_missing_smtp_setting_...`, `test_empty_smtp_setting_...`, `test_config_errors_never_contain_secret_values` |
| P1 SMTP failures | Everything retried, raw text | Permanent vs transient classification (4xx recipient refusals are transient), bounded backoff + jitter, sanitized `code`, `from None` so no raw text in traces. | `test_error_codes_and_retry_classification`, `test_transient_errors_are_retried_...`, `test_backoff_jitter_actually_varies`, integration failure tests |
| P1 TLS | No verified SSL context | `ssl.create_default_context()` for STARTTLS and SSL; fails closed; plain text only in dev/test. | `test_starttls_uses_verifying_context_...`, `test_untrusted_certificate_is_rejected_and_nothing_is_sent`, `test_trusted_certificate_delivers_over_tls`, `test_starttls_required_but_not_offered_fails_closed` |
| P1 Input validation | Basic '@' check | `email-validator` when installed, strict built-in fallback otherwise. Domain policy stays with Group 1. | `test_strict_validator_when_library_missing`, `test_validator_uses_email_validator_library_when_installed`, `test_real_email_validator_library_if_installed` (skipped if the package is missing) |
| P1 Interface/tests | No stable contract; missing tests | `EmailService` + `EmailPurpose` + typed `SendResult`; wrappers kept; full suite committed. | `test_service_*` tests |

## 4. Validation checklist (what is covered, what you must still do)
| Area | Covered by tests | You must still do |
|---|---|---|
| Repository & packaging | Suite runs from a clean extraction | Confirm README paths match the committed files; run from a clean clone; no undeclared dependency |
| Configuration | host/sender/credentials missing; port, timeout, provider, environment, TLS mode; prod rejects mock/console/file; no default secrets | Attach redacted config evidence |
| Secrets | env / `NAME_FILE` / Docker precedence; missing, unreadable, empty files; no secrets in repr/errors | Attach output |
| Email content | subjects, plain + HTML, HTML escaping, invalid input without echoing OTP | |
| SMTP success | Local test server: From/To/Subject/body, STARTTLS with a trusted test certificate, message reference | **YOU MUST DO: a real test against the approved SMTP sandbox; attach sanitized evidence** |
| SMTP failure | bad credentials, unreachable host, timeout, TLS failure, recipient rejection, 4xx/5xx, bounded retries | |
| Mock provider | memory only, clear/reset, 3000 concurrent sends with unique ids, blocked in staging/production | |
| Provider truthfulness | SES/SendGrid rejected; no simulated success without `simulated=True` | |
| Security & privacy | no OTP/passwords/addresses in logs, exceptions, traces | Document upstream auth, authorization and rate limiting with Groups 1/3 |
| Automated tests | unit + socket integration tests | **YOU MUST DO: run on your machine and attach the exact command and pass/fail summary; run the project's existing tests** |
| Integration | async contract, shared service | **YOU MUST DO: Groups 1 and 3 confirm they can import and call it; agree the result/error contract** |
| Release hygiene | `.env.example` has placeholders only | **YOU MUST DO: check Git history and the tree for the personal sender address and any credential; PR with scope, evidence, limitations** |

## 5. Known limitations
Real SMTP delivery unproven until the sandbox test; no delivery confirmation; no SES/SendGrid; no rate limiting here;
console/file/demo modes print the OTP (development only); fallback email validation is ASCII only.
