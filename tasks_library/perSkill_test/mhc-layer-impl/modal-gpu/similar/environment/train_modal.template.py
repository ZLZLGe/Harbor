import modal

app = modal.App("__APP_NAME__")

image = modal.Image.debian_slim(python_version="__PYTHON_VERSION__").pip_install(
__PIP_PACKAGES__
)

@app.function(gpu="__GPU_TYPE__", image=image, timeout=__TIMEOUT_SECONDS__)
def __FUNCTION_NAME__():
    metrics = {
        "status": "ok",
        "job": "single-training-run"
    }
    return metrics

@app.local_entrypoint()
def __ENTRYPOINT__():
    result = __FUNCTION_NAME__.remote()
    print(result)
