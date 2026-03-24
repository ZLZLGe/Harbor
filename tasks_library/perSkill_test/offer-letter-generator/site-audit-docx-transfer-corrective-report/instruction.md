请根据 `/root/site_audit_findings.json` 中的检查结果，填写 `/root/` 下文件名为 `site_audit_report_template` 的模板文件，并将完成后的结果保存到 `/root/` 下文件名为 `site_audit_report_final`、且与模板使用相同扩展名的最终文件。

模板中的占位符可能被拆分在多个文本片段中，并且会出现在正文、页脚以及嵌套的合规矩阵表格里。文档包含条件段落 `{{IF_CRITICAL_FINDINGS}}...{{END_IF_CRITICAL_FINDINGS}}`：当 `CRITICAL_FINDINGS` 为 `Yes` 时保留段落正文并移除标记；否则删除整段条件内容，最终文档里不能残留这些标记或未替换的占位符。
