# Skill Evidence

## 对照组
- Agent / 模型：`codex / gpt-5.4`
- 选用版本：`redesign_20260407`
- 这组最适合做正文对照：两边都是 `1/1` 一次通过，结果干净。

## 结果
- with-skills：`563.1s`
- without-skills：`623.3s`
- 结论：with-skills 快 `60.2s`

## 轨迹
- with-skills 轨迹：
  [2026-04-07_redesign_with_trajectory.json](./2026-04-07_redesign_with_trajectory.json)
- without-skills 轨迹：
  [2026-04-07_redesign_without_trajectory.json](./2026-04-07_redesign_without_trajectory.json)

## 为什么 with-skill 更快
- with-skills 在轨迹里更早进入浏览器验证。step `29` 就明确加载 `browser-testing` workflow，step `51` 和 step `72` 直接核对移动端冷启动、advanced 延迟加载和重复交互稳定性。
- without-skills 也能做出来，但要先自己补这套方法。它到 step `31` 才把检查项整理成计划，step `49` 和 step `53` 还先看 build artifact 和 manifest，再回到 live runtime。
- 所以这里更快，核心不是省步骤，而是 skill 把 solver 更早带到这道题真正需要的浏览器复现路径上。
