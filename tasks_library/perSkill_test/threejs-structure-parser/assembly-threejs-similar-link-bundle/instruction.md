给定场景文件 `/root/data/assembly_scene.js`，其中导出了一个 `createScene()` 函数。场景里有多层命名部件组、少量未命名中间容器，以及直接由基础几何体构成的 mesh。

你的任务是遍历场景结构，按“最近的命名祖先组”给 mesh 归属部件，并把结果写到 `/root/output`。命名组表示部件；未命名容器本身不是部件，只用于中转层级。若某个命名组下面没有归属到它的 mesh，则不要把它写入输出。

输出要求如下：

1. 为每个部件导出它直接拥有的单独 mesh OBJ，目录结构必须是：
```text
/root/output/part_meshes/<part_name>/<mesh_name>.obj
```

2. 为每个部件再导出一个合并后的 OBJ，路径必须是：
```text
/root/output/links/<part_name>.obj
```

3. 生成 `/root/output/link_index.json`，内容必须是一个 JSON 对象，并满足：
   - 顶层包含字段 `scene_file`，值为 `"assembly_scene.js"`。
   - 顶层包含字段 `parts`，值为数组。
   - `parts` 按 `part_name` 升序稳定排序。
   - 每个数组元素都必须包含以下字段：
     - `part_name`: 当前部件名。
     - `parent_part`: 当前部件最近的命名父部件名；如果没有则为 `null`。
     - `mesh_count`: 当前部件直接拥有的 mesh 数量。
     - `mesh_names`: 当前部件直接拥有的 mesh 名称数组，按升序排序。
     - `mesh_obj_files`: 与 `mesh_names` 一一对应的相对路径数组，格式为 `part_meshes/<part_name>/<mesh_name>.obj`，按升序排序。
     - `merged_obj_file`: 当前部件合并 OBJ 的相对路径，格式为 `links/<part_name>.obj`。

4. 所有 OBJ 都必须反映场景中的世界坐标结果，也就是层级上的平移、旋转、缩放都要已经烘焙进导出的几何里。

5. 嵌套的命名部件组是独立部件。父部件的合并 OBJ 和索引信息里，只能包含归属于父部件本身的 mesh，不能把子部件的 mesh 混进去。
