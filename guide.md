
背景：
我打算做的方向是技能编辑，
首先第一个工作是要做的数据管线，即我只需要提供skill，然后通过数据管线自动化的合成task，最后形成一个数据集，这个数据集将被用来做技能编辑。
技能编辑就是参考knowledge editing的工作，做一个skill editing的工作，编辑一个模型实现某一个技能的修改和添加，比如现有大模型没有这个技能，改变少量参数的情况下，要大模型能构快速遵循这个规则。

https://harborframework.com/docs 这是我即将采用的框架，设置从skill到task的管线所生成的task为harbor所定义的格式
https://skillsmp.com/zh/categories 这里面是我打算筛选的skill，我打算用这里面的skill

你的任务：
先从databases/index.ts这里面筛选出50个技能出来，放到/home/levi/Harbor文件夹下（要创建一个新的技能库文件夹，方便之后按类存放技能），注意拿到的技能要完整

你的工作流程：
