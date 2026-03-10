# Harbor

## 环境复现（推荐使用 uv）

### 前置条件
- Python：`3.12`（本仓库当前环境在 `3.12.3` 下验证）
- 已安装 `uv`

### 一键复现依赖
在仓库根目录执行：

```bash
# 创建虚拟环境（放在 .venv/，不提交到 Git）
uv venv --python 3.12 .venv

# 激活虚拟环境（Linux/macOS）
source .venv/bin/activate

# 严格按锁定版本安装依赖
uv pip sync requirements.lock
```

### 不使用 uv（可选）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
```

## 依赖锁文件

依赖版本锁定在 `requirements.lock`。
