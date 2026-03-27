## Task Description

`/app/workspace/scores.tsv` is a tab-separated file with columns:

- `student`
- `quiz`
- `midterm`
- `final`

Create `/app/workspace/transfer3.xlsx` with one sheet `report` and exactly these columns:

- `student`
- `final_score`
- `grade`

Rules:

1. Compute `final_score = 0.2*quiz + 0.3*midterm + 0.5*final`, rounded to 1 decimal.
2. Grade mapping:
   - `A` for score >= 90
   - `B` for score >= 80
   - `C` for score >= 70
   - `D` for score >= 60
   - `F` otherwise
3. Sort rows by `final_score` descending; break ties by `student` ascending.
4. Header row required. No extra sheets/columns/rows.
