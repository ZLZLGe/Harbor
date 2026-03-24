#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${TASK_WORKSPACE:-/app/workspace}"
TARGET_FILE="$WORKSPACE_ROOT/apps/pipeline/src/pipeline_sup.erl"

cat <<'EOF' > "$TARGET_FILE"
-module(pipeline_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    Queue = #{
        id => pipeline_queue,
        start => {pipeline_queue, start_link, []},
        restart => permanent,
        shutdown => 5000,
        type => worker,
        modules => [pipeline_queue]
    },
    Worker = #{
        id => pipeline_worker,
        start => {pipeline_worker, start_link, []},
        restart => permanent,
        shutdown => 5000,
        type => worker,
        modules => [pipeline_worker]
    },
    Consumer = #{
        id => pipeline_consumer,
        start => {pipeline_consumer, start_link, []},
        restart => permanent,
        shutdown => 5000,
        type => worker,
        modules => [pipeline_consumer]
    },
    Scheduler = #{
        id => pipeline_scheduler,
        start => {pipeline_scheduler, start_link, []},
        restart => permanent,
        shutdown => 5000,
        type => worker,
        modules => [pipeline_scheduler]
    },
    {ok, {{rest_for_one, 6, 5}, [Queue, Worker, Consumer, Scheduler]}}.
EOF
