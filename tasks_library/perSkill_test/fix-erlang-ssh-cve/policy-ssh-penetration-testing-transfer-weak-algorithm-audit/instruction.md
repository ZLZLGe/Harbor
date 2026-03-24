`/app/workspace` 里是一套给边缘设备生成 `sshd_config` 的 Python 策略工具。

当前审计逻辑把一批弱 KEX、cipher 和 MAC 误判成了合规项，渲染器又直接沿用了这些审计结果，导致最终生成的配置里仍然保留了已知弱算法。你需要先确认哪些算法族是被“按前缀放行”而误判的，再修复审计与配置生成逻辑。

修复后需要同时满足：

- 审计结果必须把弱 KEX、cipher 和 MAC 标成不合规
- 生成的 `sshd_config` 不能再包含这些弱算法
- 测试里要求保留的现代客户端兼容算法仍然要出现在输出配置中

把主要修改放在 `/app/workspace/policy/renderers/sshd_policy.py`，只修改提供的代码并让测试通过即可。
