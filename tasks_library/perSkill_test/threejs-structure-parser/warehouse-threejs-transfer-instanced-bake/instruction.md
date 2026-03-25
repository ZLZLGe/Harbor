给定场景文件 `/root/data/warehouse_scene.js`，其中导出了一个 `createScene()` 函数。场景里同时包含普通 `Mesh` 和多个 `THREE.InstancedMesh`，并且它们都处在多层嵌套的平移、旋转、缩放层级之下。

你的任务是把整个场景烘焙成一份单独的 OBJ，并输出一份实例统计清单。所有输出都必须写到 `/root/output`。

输出要求如下：

1. 生成 `/root/output/baked_scene.obj`。
   - 这一个 OBJ 文件必须覆盖场景中的全部可见几何。
   - 普通 `Mesh` 要按自身完整世界变换导出。
   - `THREE.InstancedMesh` 必须逐实例展开，再把节点自身的世界变换和每个实例矩阵一起烘焙到几何里。
   - 输出顶点必须已经处于最终世界坐标，不能保留未展开的实例语义。

2. 生成 `/root/output/instance_report.json`，内容必须是一个 JSON 对象，并满足：
   - 顶层字段 `scene_file` 的值必须是 `"warehouse_scene.js"`。
   - 顶层字段 `merged_obj` 的值必须是 `"baked_scene.obj"`。
   - 顶层字段 `instanced_nodes` 的值必须是数组，并按 `node_name` 升序稳定排序。
   - `instanced_nodes` 中的每个元素都必须包含：
     - `node_name`: 实例化节点名称。
     - `instance_count`: 该节点展开后的实例数量。
   - 顶层字段 `total_instances` 必须等于所有 `instance_count` 之和。
   - 顶层字段 `total_baked_primitives` 必须等于“普通 `Mesh` 数量 + 所有实例总数”。

3. 统计清单里只记录实际的 `THREE.InstancedMesh` 节点；普通 `Mesh` 不应出现在 `instanced_nodes` 中。

4. 输出必须是稳定的：同一输入下，多次运行得到的 `instanced_nodes` 排序和统计值应一致。
