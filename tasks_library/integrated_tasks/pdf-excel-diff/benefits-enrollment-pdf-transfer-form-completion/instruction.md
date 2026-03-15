You need to complete a benefits enrollment packet.

Inputs:
- `/root/benefits_enrollment_packet.pdf`: the blank enrollment packet
- `/root/employee_profile.json`: the employee data that must be transferred into the packet

Write the completed packet to:
- `/root/completed_benefits_enrollment.pdf`

Populate the packet as follows:

1. Employee information page:
   - `Employee Name`: combine `employee.first_name` and `employee.last_name` with a space.
   - `Employee ID`: `employee.employee_id`
   - `Department`: `employee.department`
   - `Work Email`: `employee.email`
   - `Phone`: `employee.phone`
   - `Home Address`: format as `street, city, state zip`
   - `Hire Date`: `employee.hire_date`
2. Plan elections page:
   - Select the medical plan that matches `elections.medical_plan`
   - Select the coverage tier that matches `elections.coverage_tier`
   - Select the dental option that matches `elections.dental_plan`
   - Mark the vision checkbox when `elections.vision_enrolled` is `true`
   - Select `Yes` or `No` for tobacco use based on `elections.tobacco_user`
   - Enter `elections.fsa.healthcare` and `elections.fsa.dependent_care` as whole-dollar numbers without commas or dollar signs
3. Dependents:
   - Copy the first two entries from `dependents` into the two dependent rows using each dependent's `name`, `relationship`, and `date_of_birth`
   - If a dependent row has no matching entry, leave that row blank
4. Signature:
   - `Employee Signature`: `signature.name`
   - `Date`: `signature.date`

Requirements:
- Preserve the existing packet content and structure.
- Do not add extra pages.
- The completed PDF must remain readable as a normal PDF document.
