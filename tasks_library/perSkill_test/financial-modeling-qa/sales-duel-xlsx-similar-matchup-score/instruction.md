Please analyze the campaign workbook in `/root/`. It is the only file there whose name starts with `campaign_showdown`.

The workbook contains multiple distraction sheets, an archived export mixed into the same tab as the current campaign board, a rules sheet, and a hidden correction block. Find the active campaign data region, apply the scoring rules in the workbook to compute each campaign's final score, and then compare adjacent odd and even campaign numbers as head-to-head matchups:

- campaign 01 vs 02
- campaign 03 vs 04
- campaign 05 vs 06
- and so on

If the odd-numbered campaign in a pair has the higher score, count that matchup as one win for the odd side. If the even-numbered campaign has the higher score, count it as one win for the even side. Ignore ties.

Write the value of:

`(odd-side wins) - (even-side wins)`

to `/root/campaign_margin.txt`.

For the answer, write only the number.
