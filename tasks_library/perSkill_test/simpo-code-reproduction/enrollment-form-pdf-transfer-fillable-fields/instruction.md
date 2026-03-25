请阅读 `/root/enrollment/forms/employee_enrollment_form` 和 `/root/enrollment/intake_profile.json`，生成 `/root/enrollment_field_values.json`。

输出必须是一个 JSON 数组，并且要覆盖该表单中全部可填写字段。数组中的每个元素都必须包含以下字段：

- `field_id`: 表单中该字段的真实字段 ID。
- `page`: 该字段所在页码。
- `description`: 对这个字段用途的简短说明。
- `value`: 要写入该字段的值。

要求：

1. 不要猜测字段名、页码或选项值，必须以表单里的真实元数据为准。
2. 文本框写入资料 JSON 中对应的字符串内容。
3. 下拉框必须写入底层 option value，不要写界面展示文本。
4. 单选组必须写入被选项的底层 export value。
5. 复选框无论最终是否勾选，都必须出现在输出里；未勾选时也要写入该字段合法的 unchecked value。
6. 输出里不要包含不存在的字段，也不要漏掉任何一个可填写字段。
7. 不要修改输入文件。
