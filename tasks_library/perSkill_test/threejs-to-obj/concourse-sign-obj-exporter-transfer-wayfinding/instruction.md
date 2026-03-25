你需要把一个导视牌坯件场景导出成 Blender 可直接导入的 OBJ 文件，供 CNC 打样前审阅。

输入模块位于 `/root/data/wayfinding_scene.js`，其中导出 `buildWayfindingSignScene()`。场景里包含一个由 `Shape` 加 `ExtrudeGeometry` 生成的牌面坯件、一个背部连接板、两根立柱，以及两个由 `LatheGeometry` 生成的帽头。

请编写脚本，生成 `/root/output/wayfinding_sign.obj`，并满足下面的输出契约：

1. OBJ 必须只包含这 6 个实体零件，并分别写成独立的 `o` object 记录：`panel_blank`、`back_strap`、`left_post`、`right_post`、`left_finial`、`right_finial`。
2. 导出时必须保留每个零件在场景中的最终世界空间位置和姿态，不能退回局部坐标后重新摆放。
3. 写出 OBJ 之前，要把整个结果从 Three.js 的 Y-up 坐标转换到 Blender 常用的 Z-up 坐标，也就是整体应用 `-90` 度 X 轴旋转。
4. `panel_blank` 必须保留真实挤出厚度，并且 4 个安装孔不能被填平、删掉或改位。该对象的 `userData` 中已经给出了 `mountingHoleCenters`、`mountingHoleRadius` 和 `panelThickness` 供你核对。
5. 两个帽头必须保留车削后的旋转体外形，不能被替换成简化盒体，也不能和别的零件合并到同一个 OBJ object。
6. 输出必须是标准 OBJ 文本，至少包含顶点和面数据。

验证只依据可观察结果进行：

- 检查 `/root/output/wayfinding_sign.obj` 是否存在且是有效 OBJ。
- 检查是否正好导出了 6 个约定对象，以及每个对象都包含实际几何。
- 检查 `panel_blank` 的最终厚度、局部包围盒朝向和 4 个安装孔的孔位是否正确；厚度与包围盒数值比较按绝对误差 `1e-5` 判定。
- 检查两个帽头的旋转体轮廓样本点仍然存在，以确认最终几何拓扑没有被错误简化；采样点存在性按坐标四舍五入到小数点后 `5` 位判定。
