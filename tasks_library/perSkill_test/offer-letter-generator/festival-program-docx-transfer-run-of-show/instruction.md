请根据 `/root/festival_run_of_show_data.json` 中的演出日程与现场联系人信息，填写 `/root/` 下文件名为 `festival_run_of_show_template` 的模板文件，并将完成后的结果保存到 `/root/` 下文件名为 `festival_run_of_show_final`、且与模板使用相同扩展名的最终文件。

模板中的占位符可能被拆分在多个文本片段中，会出现在正文、页脚以及舞台准备嵌套表格里。文档还包含条件段落 `{{IF_RAIN_PLAN}}...{{END_IF_RAIN_PLAN}}`：当 `RAIN_PLAN_ENABLED` 为 `Yes` 时保留段落正文并移除标记，否则删除整段条件内容；最终文档里不能残留这些标记或未替换的占位符。
