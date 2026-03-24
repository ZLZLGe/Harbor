In `/app/workspace/` I provided a Flink job skeleton together with a small synthetic pipeline-operations dataset.

The input files are:

- `/app/workspace/data/pipeline_task_lifecycle.csv.gz`
- `/app/workspace/data/pipeline_close_events.csv.gz`
- `/app/workspace/data/schema_notes.md`

All timestamps are ISO-8601 UTC strings.

## Task

In `/app/workspace/src/main/java/pipelinesla/query/PipelineCloseoutSlaRollup.java`, implement a Flink job that rolls up backlog SLA metrics for each pipeline once its close event arrives.

Each lifecycle record belongs to one `(pipeline_id, task_id)` and has an `event_type`:

- `BLOCKED`: the task enters backlog and contributes to the pipeline's active backlog.
- `READY`: the task leaves backlog successfully.
- `FAILED`: the task counts toward the pipeline's failed task total; if it is currently blocked, it also leaves backlog immediately.

A pipeline backlog interval is a maximal continuous event-time interval during which at least one task is currently blocked for that pipeline.

Apply these rules:

1. A backlog interval starts when the blocked-task count for a pipeline changes from `0` to `> 0`.
2. A backlog interval ends when the blocked-task count returns to `0`.
3. The affected task count of one backlog interval is the number of distinct `task_id` values that were blocked at any point during that interval.
4. `failed_task_count` is the number of distinct `task_id` values that have at least one `FAILED` event before that pipeline's close event.
5. If the pipeline is still backlog-active when the close event arrives, close the current backlog interval at the close timestamp.
6. Ignore lifecycle events that happen after the close event.
7. Pipelines without a close event must not produce output.
8. If multiple backlog intervals have the same longest duration, choose the one with the earliest start time. The `backlog_task_count` must come from that chosen interval.
9. If a closed pipeline never has a backlog interval, output `0` for both `longest_backlog_micros` and `backlog_task_count`.

Line order is not important.

## Output

Write `/app/workspace/pipeline_sla_rollup.txt` with one line per closed pipeline in this exact format:

`pipeline=<pipelineId> longest_backlog_micros=<duration> backlog_task_count=<count> failed_task_count=<count>`

## Input Parameters

- `task_input`: path to a single gzipped lifecycle CSV file
- `close_input`: path to a single gzipped pipeline-close CSV file
- `output`: path to the output file

## Provided Code

- `/app/workspace/src/main/java/pipelinesla/query/PipelineCloseoutSlaRollup.java`: provided Flink job skeleton. Do not change the class name.
- `/app/workspace/src/main/java/pipelinesla/utils/AppBase.java`: base helpers already provided.
- `pom.xml`: defines the job class and jar name. Do not change this file.

You may add supporting classes under `pipelinesla.datatypes`, `pipelinesla.sources`, and `pipelinesla.utils` if needed.
