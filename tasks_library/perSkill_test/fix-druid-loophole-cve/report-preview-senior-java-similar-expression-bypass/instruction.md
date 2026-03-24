报表平台的预览服务位于 `/root/report-service`。当前的 `/api/reports/preview` 接口为了兼容旧请求，会扫描未知的顶层对象字段，并把其中的 `allowExpressions` 标记偷偷合并进预览选项。攻击者可以构造带有空字符串字段或兼容包装字段的畸形请求，在预览阶段触发 SpEL 表达式求值，读取服务器上的敏感信息。

你需要完成下面几件事：

1. 生成补丁文件 `/root/patches/0001-block-expression-preview-bypass.patch`
2. 将补丁应用到 `/root/report-service`
3. 重新构建服务：

```bash
cd /root/report-service
mvn -q -DskipTests package
```

验证器会启动你构建后的服务，并检查两类行为：

- 利用畸形顶层字段打开表达式执行的请求必须在执行前被拒绝
- 正常的模板预览请求必须继续返回正确结果

不要修改补丁输出路径。
