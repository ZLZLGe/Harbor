请根据 `/root/patient_profile.json` 和 `/root/visit_note.txt`，将空白入院表 `/root/clinic_intake_form.pdf` 填写完整，并输出为 `/root/completed_intake_form.pdf`。

要求：
- 保持输出为 PDF 文件。
- 需要填写所有能从输入中明确确定的字段。
- `patient_name` 使用 `given_name` 和 `family_name` 按 `名 姓` 拼接。
- 所有日期保持 `YYYY-MM-DD`。
- `allergies` 与 `current_medications` 分别用 `; ` 连接列表内容。
- 备注中明确要求的布尔项需要勾选；没有提到的不要额外勾选。
- 不要修改表单版式或生成额外文件作为最终答案。
