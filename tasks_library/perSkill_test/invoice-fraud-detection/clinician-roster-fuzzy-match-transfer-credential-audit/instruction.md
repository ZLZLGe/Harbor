Review these files:
- `/root/shift_roster.csv`: clinician assignments exported from staffing operations.
- `/root/licensing_registry.csv`: canonical clinician registry with license numbers, credential levels, status, and expiration dates.

Write `/root/license_exceptions.csv` containing only the roster assignments that should be escalated for credential review.

An assignment should be flagged if it meets any of the following conditions:
1. `Unresolved Clinician`: the roster name cannot be reliably matched to any clinician in the registry. Names may include initials, reordered tokens, dropped punctuation, or small spelling errors.
2. `License Number Mismatch`: the roster name can be matched, but the reported license number does not equal the matched registry license number.
3. `Credential Mismatch`: the roster name can be matched and the license number matches, but the registry `credential_level` does not equal the roster `required_credential`.
4. `Inactive License`: the roster name can be matched and the license number matches, but the registry `status` is not `Active`.
5. `Expired License`: the roster name can be matched and the license number matches, the status is `Active`, but `expires_on` is earlier than the roster `shift_date`.

If multiple conditions apply, use the first matching reason in the order above.

Output requirements:
- Write a CSV file with this exact header order:
  `assignment_id,shift_date,unit,clinician_alias,reported_license_number,matched_license_number,matched_registry_name,reason`
- Preserve the original roster alias in `clinician_alias`.
- For `Unresolved Clinician`, leave `matched_license_number` and `matched_registry_name` empty.
- Sort the output rows by `assignment_id` ascending.
- Do not include clean assignments.
