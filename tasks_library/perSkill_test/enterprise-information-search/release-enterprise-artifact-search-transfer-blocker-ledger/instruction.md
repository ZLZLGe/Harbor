你需要在一组发布 war-room 工件中，为指定 release candidate 生成一份阻塞项账本。

输入位置：
- 请求说明：`/root/release_request.json`
- 工件目录：`/root/war_room/`

你的目标：
1. 根据请求说明中的 release candidate，只保留当前候选版本在发布时点仍然成立的真实 blocker。
2. 对每个真实 blocker，输出它的 owner 员工 ID。
3. 找到与该 blocker 直接关联、用于修复当前 release candidate 的 PR。
4. 给出该 blocker 最近一次状态更新的证据，并用 artifact pointer 指到具体记录。
5. 列出截至当前发布时点仍缺失的 sign-off。

注意事项：
- 数据里混有历史 release candidate、已降级为 follow-up 的伪 blocker、重复/umbrella 记录和已经解除阻塞的旧条目，不能误收录。
- 只有同时满足“属于目标 release candidate”“仍然阻塞发布”“没有被明确降级或关闭”的条目，才算真实 blocker。
- `owner_employee_id` 必须是员工 ID，不要输出姓名。
- `fix_pr` 必须是直接用于修复该 blocker 的 PR；不要填仅讨论问题、仅同步状态、或属于其他 release candidate 的 PR。
- `latest_status.artifact_pointer` 必须指向最近一次状态更新所在的具体消息、会议记录或 tracker 更新，不能只指到目录级文件。
- `missing_signoffs` 只能保留当前仍未完成的 sign-off；已经完成、被豁免、或属于其他 blocker 的 sign-off 都不能输出。
- `artifact_pointer` 必须是相对 `/root` 的路径字符串，并带 `#...` 片段定位到具体记录。
- 所有列表必须去重并按字典序稳定排序；`blockers` 按 `blocker_id` 升序输出，`missing_signoffs` 按 `team` 升序输出。

将结果写入 `/root/release_blocker_ledger.json`，JSON 结构必须如下：

```json
{
  "release_candidate": "目标 release candidate",
  "blockers": [
    {
      "blocker_id": "BLK-000",
      "title": "阻塞项标题",
      "owner_employee_id": "eid_xxx",
      "fix_pr": {
        "pr_id": "PR-000",
        "artifact_pointer": "war_room/...#..."
      },
      "latest_status": {
        "summary": "最近一次状态更新的简短摘要",
        "artifact_pointer": "war_room/...#..."
      },
      "missing_signoffs": [
        {
          "team": "Security",
          "artifact_pointer": "war_room/...#..."
        }
      ]
    }
  ]
}
```

除了这个 JSON 文件，不需要额外输出其他答案文件。
