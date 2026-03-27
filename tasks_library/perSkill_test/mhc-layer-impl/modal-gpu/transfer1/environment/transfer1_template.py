import modal

app = modal.App("mhc-transfer-batch")

base_image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch",
    "numpy"
)

__FUNCTION_BLOCKS__

@app.local_entrypoint()
def main():
    results = []
__ENTRYPOINT_CALLS__
    print(results)
