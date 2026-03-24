`/opt/syzkaller/sys/linux/dev_uinput.txt` 的骨架已经准备好，请不要重写它。

你的任务是补齐 companion 常量文件：

- `/opt/syzkaller/sys/linux/dev_uinput.txt.const`

要求：

- 只为 `amd64` 和 `386` 提供常量。
- 覆盖骨架里已经引用到的 uinput ioctl、事件类型以及能力位常量。
- 常量值应与 Linux UAPI 头文件和 ioctl 编码规则一致。
- 让下面的命令通过：

```bash
cd /opt/syzkaller
make descriptions
```

这个任务的输出物只有 `.const` 文件；现有的 `dev_uinput.txt` 应保持原样。
