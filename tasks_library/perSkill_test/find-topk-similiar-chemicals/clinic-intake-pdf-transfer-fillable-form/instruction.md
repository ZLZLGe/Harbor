你要把一份患者信息 JSON 转写到一份可编辑门诊登记表单中。

输入文件：
- `/root/data/clinic_intake_form`：1 页门诊登记表单文档，里面已经包含可编辑字段。
- `/root/data/patient_payload.json`：患者信息。

请生成 `/root/workspace/completed_intake.pdf`，要求如下：

1. 基于原始表单生成填写完成的版本，输出后仍需保留原有可编辑字段，便于程序再次读取字段值。
2. 需要正确填写这些可见栏目：
   - `Last Name` ← `patient.legal_name.last`
   - `Preferred First Name` ← `patient.legal_name.first`
   - `Date of Birth (YYYY-MM-DD)` ← `patient.birth_date`
   - `Mobile Phone` ← `patient.contact.mobile`
   - `Known Allergies` ← `patient.clinical_flags.allergies`
3. `patient.appointment.track` 只会是 `new_patient` 或 `follow_up`，你必须在 `Visit Type` 中只选中对应的单选项。
4. 两个复选框的填写规则如下：
   - `Text appointment reminders` ← `patient.preferences.sms_reminders`
   - `Received privacy notice` ← `patient.acknowledgements.privacy_notice_received`
   布尔值为 `true` 时选中，为 `false` 时取消选中。
5. 表单里的默认勾选状态不一定和 JSON 一致，最终结果必须以 JSON 为准。
6. 原始表单字段名不保证与 JSON 键完全一致；先识别字段，再写值。
7. 除了上述栏目，不需要额外添加页面、图片或说明文字。
