请根据 `/root/patient_discharge_data.json` 中的出院数据，填写 `/root/` 下文件名为 `discharge_packet_template` 的模板文件，并将完成后的结果保存到 `/root/` 下文件名为 `discharge_packet_final`、且与模板使用相同扩展名的最终文件。

模板中的占位符可能被拆分在多个文本片段中，且会出现在正文与页眉里。文档包含两个需要更新的嵌套表格：一个用于药物清单，另一个用于复诊安排；你需要把模板中的占位行替换成数据中的全部条目，最终不能残留示例占位符。模板还包含条件段落 `{{IF_REMOTE_FOLLOWUP}}...{{END_IF_REMOTE_FOLLOWUP}}`：当 `REMOTE_FOLLOWUP_REQUIRED` 为 `Yes` 时保留段落正文并移除标记，否则删除整段条件内容。
