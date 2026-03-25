容器里已经准备好一份 syzkaller 源码树，但 `/dev/watchdog#` 对应的描述文件还没有补完。你会拿到一份精简后的 watchdog UAPI 摘录：`/task-assets/watchdog_uapi_excerpt.h`。

请创建两个文件：

- `/opt/syzkaller/sys/linux/dev_watchdog_ctl.txt`
- `/opt/syzkaller/sys/linux/dev_watchdog_ctl.txt.const`

要求如下：

1. `.txt` 文件必须包含 `include <linux/watchdog.h>`。
2. 为 watchdog 设备定义 `resource fd_watchdog[fd]`。
3. 添加一个针对 `/dev/watchdog#` 的 opener，返回 `fd_watchdog`。
4. 定义 `watchdog_info` 结构，字段与摘录一致：
   - `options`，并使用 `flags[watchdog_status_flags, int32]`
   - `firmware_version`
   - `identity[32]`
5. 为下面这些核心 ioctl 补出描述，并使用正确的参数方向或无参数形式：
   - `WDIOC_GETSUPPORT`: `ptr[out, watchdog_info]`
   - `WDIOC_GETSTATUS`: `ptr[out, int32]`
   - `WDIOC_GETBOOTSTATUS`: `ptr[out, int32]`
   - `WDIOC_GETTEMP`: `ptr[out, int32]`
   - `WDIOC_SETOPTIONS`: `ptr[in, flags[watchdog_set_options, int32]]`
   - `WDIOC_KEEPALIVE`: 不带第三个参数
   - `WDIOC_SETTIMEOUT`: `ptr[inout, int32]`
   - `WDIOC_GETTIMEOUT`: `ptr[out, int32]`
   - `WDIOC_SETPRETIMEOUT`: `ptr[inout, int32]`
   - `WDIOC_GETPRETIMEOUT`: `ptr[out, int32]`
   - `WDIOC_GETTIMELEFT`: `ptr[out, int32]`
6. 需要定义两个 flags 集：
   - `watchdog_status_flags`: 覆盖摘录里的全部 `WDIOF_*` 位
   - `watchdog_set_options`: 覆盖摘录里的全部 `WDIOS_*` 位
7. `.const` 文件必须：
   - 使用 `arches = amd64, 386`
   - 至少包含 `.txt` 中实际引用到的全部 `WDIOC_*`、`WDIOF_*` 和 `WDIOS_*` 常量值

补充说明：

- 以 `/task-assets/watchdog_uapi_excerpt.h` 为题面依据。
- 这份接口里有两个需要特别注意的地方：
  - `WDIOC_SETOPTIONS` 在建模时应视为“用户向内核传入选项位”。
  - `WDIOC_KEEPALIVE` 可以建模成无 payload 的 ioctl。
- 验证时会运行 `make descriptions`，并把你的关键签名与容器里的 `<linux/watchdog.h>` 对照检查。
