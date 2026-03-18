请根据 `/root/packet_page_order.txt` 的页序清单，从提供的会议材料 PDF 中抽取指定页面，按清单顺序合并，并将最终结果保存为 `/root/board_meeting_packet.pdf`。

输入材料：
- `/root/agenda_brief.pdf`
- `/root/finance_review.pdf`
- `/root/product_update.pdf`
- `/root/governance_appendix.pdf`

要求：
- 只保留页序清单中列出的页面，顺序必须完全一致。
- 清单中标注需要旋转的页面，必须在最终输出中恢复为正向可读。
- 不要额外插入封面、分隔页、书签或其他文件。
- 最终答案只能是 `/root/board_meeting_packet.pdf`。
