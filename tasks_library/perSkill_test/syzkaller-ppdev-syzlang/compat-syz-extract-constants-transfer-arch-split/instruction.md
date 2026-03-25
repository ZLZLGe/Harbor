一段 mock compat 设备的描述已经准备好了，问题只在 companion 常量文件：当前 `/opt/syzkaller/sys/linux/dev_demo_compat.txt.const` 把一组 ioctl 当成了统一数值，结果把 `amd64` 的编码错误地复用到了 `386`。

环境里已有这些输入：

- `/opt/syzkaller/sys/linux/dev_demo_compat.txt`
- `/opt/syzkaller/sys/linux/dev_demo_compat.txt.const`（故意写错）
- `/opt/task-assets/mock-uapi/linux/dev_demo_compat.h`
- `/opt/task-assets/compat_manifest.json`

请只修复这个输出文件：

- `/opt/syzkaller/sys/linux/dev_demo_compat.txt.const`

要求如下：

- 保留 `arches = amd64, 386`
- 文件里至少覆盖这些符号：
  - `DEMO_IOCTL_PEEK`
  - `DEMO_IOCTL_POKE`
  - `DEMO_IOCTL_XACT`
  - `DEMO_IOCTL_PING`
  - `DEMO_MODE_STRICT`
  - `DEMO_MODE_BULK`
  - `DEMO_FLAG_SHARED`
  - `DEMO_FLAG_TRACE`
- `DEMO_IOCTL_PEEK`、`DEMO_IOCTL_POKE`、`DEMO_IOCTL_XACT` 必须按架构拆开写，使用这种格式：
  - `NAME = amd64:<value>, 386:<value>`
- 数值相同的常量可以继续写成单值
- 头文件和现成的 `.txt` 描述不要改；这道题只要求把 `.const` 修正确

提示：

- 这几个分叉的 ioctl 都是 `_IO*` 编码，区别来自结构体大小
- `demo_snapshot` 里有 `unsigned long`
- `demo_user_ref` 里有用户指针

可用下面两条命令分别校验两个架构：

```bash
python3 /opt/task-assets/verify_demo_compat.py amd64
python3 /opt/task-assets/verify_demo_compat.py 386
```
