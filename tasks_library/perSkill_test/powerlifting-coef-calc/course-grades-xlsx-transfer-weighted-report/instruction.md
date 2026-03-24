请完成 `/root/data/` 目录中的课程成绩报告工作簿。

这个工作簿包含四个工作表：
- `Roster`：学生名单，列为 `StudentID`、`Section`、`LastName`、`FirstName`
- `Scores`：成绩表，列为 `StudentID`、`Quiz1`、`Quiz2`、`Quiz3`、`Quiz4`、`Lab1`、`Lab2`、`Midterm`、`FinalExam`
- `Weights`：权重表，列为 `Category`、`Weight`
- `Report`：空白工作表，等待你填写

请在 `Report` 中从 `A1` 开始建立以下列，顺序必须一致：
`StudentID`、`Section`、`LastName`、`FirstName`、`Quiz1`、`Quiz2`、`Quiz3`、`Quiz4`、`DroppedQuiz`、`QuizAverage`、`Lab1`、`Lab2`、`LabAverage`、`Midterm`、`FinalExam`、`QuizWeighted`、`LabWeighted`、`MidtermWeighted`、`FinalWeighted`、`TotalScore`、`LetterGrade`

要求：
1. 将 `Roster` 中的 `StudentID`、`Section`、`LastName`、`FirstName` 按原行顺序复制到 `Report`。
2. `Quiz1` 到 `Quiz4`、`Lab1`、`Lab2`、`Midterm`、`FinalExam` 必须使用工作簿公式，根据当前行的 `StudentID` 从 `Scores` 中取值。
3. `DroppedQuiz` 必须使用工作簿公式，取当前学生四次小测中的最低分。
4. `QuizAverage` 必须使用工作簿公式，丢弃最低一次小测后，对剩余三次小测求平均，并保留两位小数。
5. `LabAverage` 必须使用工作簿公式，计算两次实验的平均分，并保留两位小数。
6. `QuizWeighted`、`LabWeighted`、`MidtermWeighted`、`FinalWeighted` 必须使用工作簿公式，从 `Weights` 中匹配对应权重后计算加权分，并保留两位小数。
7. `TotalScore` 必须使用工作簿公式，对四个加权分求和，并保留两位小数。
8. `LetterGrade` 必须使用工作簿公式按以下规则判定：`TotalScore >= 90` 为 `A`，`>= 80` 为 `B`，`>= 70` 为 `C`，`>= 60` 为 `D`，否则为 `F`。
9. 不要把结果手工写死；需要保留可重算的公式。
10. 保持 `Roster`、`Scores` 和 `Weights` 原样不变，并将结果保存回原文件。
