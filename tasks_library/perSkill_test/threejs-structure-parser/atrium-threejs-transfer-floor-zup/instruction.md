给定场景文件 `/root/data/atrium_scene.js`，其中导出了一个 `createScene()` 函数。场景表示一个多层中庭建筑；命名 `Group` 表示楼层，未命名容器只用于层级中转，不算楼层。

你的任务是按“最近的命名楼层祖先”收集 mesh 归属，导出每层的合并 OBJ，并生成楼层清单。所有输出都必须写到 `/root/output`。

输出要求如下：

1. 在导出前，先把场景统一从 Y-up 转成 Z-up。
   - 这个转换固定为：对要导出的几何整体应用一次绕 X 轴 `-90°` 的旋转。
   - 输出 OBJ 顶点必须已经处在转换后的 Z-up 坐标系中。

2. 为每个有直属几何的楼层导出一个合并 OBJ，路径必须是：
```text
/root/output/floors/<floor_name>.obj
```
   - 楼层是任意深度的命名 `Group`。
   - mesh 归属于最近的命名楼层祖先。
   - 父楼层的 OBJ 只能包含归属于父楼层自身的 mesh，不能把子楼层的 mesh 合并进去。
   - 如果某个命名楼层在排除子楼层后没有直属 mesh，不要为它生成 OBJ，也不要把它写进清单。

3. 生成 `/root/output/floor_manifest.json`，内容必须是一个 JSON 对象，并满足：
   - 顶层字段 `scene_file` 的值必须是 `"atrium_scene.js"`。
   - 顶层字段 `axis_conversion` 的值必须是 `"Y-up to Z-up"`。
   - 顶层字段 `floors` 的值必须是数组，并按 `floor_name` 升序稳定排序。
   - `floors` 中的每个元素都必须包含以下字段：
     - `floor_name`: 当前楼层名称。
     - `parent_floor`: 当前楼层最近的命名父楼层名称；如果没有则为 `null`。
     - `mesh_count`: 当前楼层直属 mesh 数量。
     - `merged_obj_file`: 当前楼层合并 OBJ 的相对路径，格式为 `floors/<floor_name>.obj`。

4. 输出必须稳定：同一输入下，多次运行得到的楼层排序、文件名和几何结果应一致。
