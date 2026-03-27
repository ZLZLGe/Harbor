# Score Syntax Translation Quiz Attempts

Input files:
- `/root/quiz_answer_key.json`
- `/root/quiz_attempts.json`

Create exactly one file:
- `/outputs/syntax_mapping_scoreboard.json`

Output contract:
1. Output must be a JSON object with keys:
   - `generated_from`
   - `total_questions`
   - `participants`
   - `top_performer`
2. `participants` must be an array sorted by:
   - highest `accuracy_percent` first
   - then participant name ascending
3. Each participant item must include:
   - `participant`
   - `correct`
   - `total`
   - `accuracy_percent`
   - `missed_case_ids`
4. `accuracy_percent` must be rounded to one decimal place.

Success criteria:
- `/outputs/syntax_mapping_scoreboard.json` exists and matches the required scoring results.
