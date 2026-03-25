你要把几份现场资料重新装订成一份最终资料包。

输入文件：
- `/root/data/assembly_order.txt`：装订说明。每个有效步骤一行，格式为 `<序号> | <文件名> | page <页码> | rotate <角度>`。页码从 1 开始，角度表示顺时针旋转角度。
- `/root/data/gate_briefing.pdf`
- `/root/data/crew_packets.pdf`
- `/root/data/crane_path_sheet.pdf`
- `/root/data/permit_stack.pdf`

请生成 `/root/workspace/site_packet.pdf`，要求如下：

1. 严格按照装订说明列出的顺序抽取并合并页面，只能使用说明中点名的页面。
2. `rotate` 不是 `0` 时，必须先按该顺时针角度旋转对应页面，再写入最终资料包。
3. 输出文件总页数必须与装订说明中的步骤数一致，不得插入空白页、封面或额外说明页。
4. 最终资料包中的每一页都必须保留原页面正文文本，便于程序再次抽取核对。
5. 不需要提交中间文件；只需生成最终的 `/root/workspace/site_packet.pdf`。
