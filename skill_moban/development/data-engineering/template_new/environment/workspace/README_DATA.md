# Workspace Notes

Run the task with:

```bash
bash /app/workspace/run.sh --output /app/answer
```

The runner starts ClickHouse, recreates the `raw` and `analytics` databases,
loads the files from `DATA_DIR`, runs `/app/workspace/sql/build_waves.sql`,
and exports the required answer files.

`DATA_DIR` defaults to `/app/workspace/data` and may be overridden with an
alternate directory containing the same folder and file names.
