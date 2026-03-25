Use the q2 and q3 13F snapshots already available in `/root/2025-q2` and `/root/2025-q3`.

Answer these four questions and write `/root/similar_answers.json` as JSON with this exact schema:

```json
{
  "q1_answer": 0.0,
  "q2_answer": 0,
  "q3_answer": ["string", "string", "string", "string"],
  "q4_answer": ["string", "string", "string"]
}
```

Questions:

1. For `VIKING GLOBAL INVESTORS LP`, what is the total q3 reported value across all q3 holdings rows?
2. For `VIKING GLOBAL INVESTORS LP`, how many q3 holdings rows are stock-equivalent positions only?
3. For `Pershing Square Capital Management, L.P.`, compare q3 against q2 using stock-equivalent positions only. Which four CUSIPs have the largest positive value deltas, ordered from largest delta to smaller delta?
4. For q3 CUSIP `11135F101`, which three managers have the largest reported value, ordered from largest to smaller?
