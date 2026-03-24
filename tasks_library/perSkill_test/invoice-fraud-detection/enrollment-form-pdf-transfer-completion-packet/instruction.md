Use the applicant record in `/root/applicant_profile.json` to complete the template file in `/root/` whose stem is `enrollment_packet_template`.

- The template file uses the same lowercase three-letter document suffix as the completed packet should use.
- Write the finished packet to `/root/completed_enrollment_packet` with that same suffix.

Rules:
- Keep the page count and page order unchanged.
- Pages 1 and 4 already contain built-in form fields. Fill those fields directly instead of replacing them with page-level text.
- For the blank areas without built-in fields, add typed text or `X` marks in the intended blank region or checkbox square.
- Use only the applicant JSON as the source of truth.

Field mapping:

Page 1 built-in fields:
- `legal_name` <- `legal_name`
- `preferred_name` <- `preferred_name`
- `date_of_birth` <- `date_of_birth`, formatted as `MM/DD/YYYY`
- `student_id` <- `student_id`
- `program_name` <- `program_name`
- `start_term` <- `start_term`
- `email` <- `email`
- `mobile_phone` <- `mobile_phone`

Page 2 blank areas:
- Street / Unit line <- `mailing_address.line1`
- City / Region / Postal Code / Country line <- `city / region / postal_code / country`
- Emergency Contact Name <- `emergency_contact.name`
- Relationship <- `emergency_contact.relationship`
- Contact Phone <- `emergency_contact.phone`
- Residency Status:
  - mark `International` if `citizenship` is `International`
  - otherwise mark `Domestic`
- Orientation Add-ons Requested:
  - mark every option listed in `orientation_addons`

Page 3 blank areas:
- Previous Institution <- `previous_institution`
- Accepted Transfer Credits <- `transfer_credits_accepted`
- Attendance Mode: mark the option matching `attendance_mode`
- Housing Plan: mark the option matching `housing_plan`
- Support / Accessibility Note <- `support_note`

Page 4:
- Built-in field `typed_signature` <- `typed_signature`
- Built-in field `completion_date` <- `completion_date`, formatted as `MM/DD/YYYY`
- Directory Listing Preference:
  - mark `Allow` if `communication_preferences.directory_opt_in` is true
  - otherwise mark `Do Not Allow`
- SMS Alerts Preference:
  - mark `Allow` if `communication_preferences.sms_alerts` is true
  - otherwise mark `Do Not Allow`
- Acknowledgements:
  - mark the checkbox only if `financial_terms_accepted` is true
