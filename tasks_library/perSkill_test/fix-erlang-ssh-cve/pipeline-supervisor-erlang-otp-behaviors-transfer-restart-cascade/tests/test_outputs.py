import os
import subprocess
import textwrap
from pathlib import Path

import pytest


WORKSPACE = Path(os.environ.get("TASK_WORKSPACE", "/app/workspace"))
SOURCE_DIR = WORKSPACE / "apps" / "pipeline" / "src"
EBIN_DIR = Path(f"/tmp/pipeline-supervisor-ebin-{os.getpid()}")


def _run(cmd: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout
    )


def _compile_modules() -> None:
    EBIN_DIR.mkdir(parents=True, exist_ok=True)
    sources = sorted(str(path) for path in SOURCE_DIR.glob("*.erl"))
    assert sources, f"no Erlang sources found in {SOURCE_DIR}"
    proc = _run(["erlc", "-o", str(EBIN_DIR), *sources], timeout=60)
    assert proc.returncode == 0, (
        "failed to compile pipeline sources\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}\n"
    )


def _erl_eval(expr: str) -> str:
    proc = _run(
        [
            "erl",
            "-noshell",
            "-pa",
            str(EBIN_DIR),
            "-eval",
            expr,
            "-s",
            "init",
            "stop"
        ],
        timeout=60
    )
    assert proc.returncode == 0, (
        "erl evaluation failed\n"
        f"expr:\n{expr}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}\n"
    )
    return proc.stdout


@pytest.fixture(scope="session", autouse=True)
def _build_once() -> None:
    assert SOURCE_DIR.exists(), f"missing source dir: {SOURCE_DIR}"
    _compile_modules()


def test_crash_restarts_processing_chain_and_drains_queue() -> None:
    expr = textwrap.dedent(
        """
        {ok, SupPid} = pipeline_sup:start_link(),
        unlink(SupPid),
        ChildrenBefore = maps:from_list([
            {Id, Pid}
            || {Id, Pid, _Type, _Modules} <- supervisor:which_children(pipeline_sup)
        ]),
        ok = pipeline_queue:enqueue(job_alpha),
        ok = pipeline_queue:enqueue({crash_once, batch_beta}),
        ok = pipeline_queue:enqueue(job_gamma),
        WaitCompleted =
            fun Self(0) ->
                    erlang:error({timeout, pipeline_queue:snapshot()});
                Self(AttemptsLeft) ->
                    Snapshot = pipeline_queue:snapshot(),
                    case maps:get(completed, Snapshot) of
                        [job_alpha, {crash_once, batch_beta}, job_gamma] = Completed ->
                            Completed;
                        _ ->
                            timer:sleep(40),
                            Self(AttemptsLeft - 1)
                    end
                    end,
        Completed = WaitCompleted(100),
        ChildrenAfter = maps:from_list([
            {Id, Pid}
            || {Id, Pid, _Type, _Modules} <- supervisor:which_children(pipeline_sup)
        ]),
        QueueSnapshot = pipeline_queue:snapshot(),
        io:format(
            "SUP_ALIVE=~p~nWORKER_RESTARTED=~p~nCONSUMER_RESTARTED=~p~nSCHEDULER_RESTARTED=~p~nCOMPLETED=~p~nPENDING=~p~nLEASES=~p~n",
            [
                erlang:is_process_alive(SupPid),
                maps:get(pipeline_worker, ChildrenBefore) =/= maps:get(pipeline_worker, ChildrenAfter),
                maps:get(pipeline_consumer, ChildrenBefore) =/= maps:get(pipeline_consumer, ChildrenAfter),
                maps:get(pipeline_scheduler, ChildrenBefore) =/= maps:get(pipeline_scheduler, ChildrenAfter),
                Completed,
                maps:get(pending, QueueSnapshot),
                maps:get(leases, QueueSnapshot)
            ]
        ),
        exit(SupPid, shutdown).
        """
    ).strip()

    output = _erl_eval(expr)

    assert "SUP_ALIVE=true" in output, output
    assert "WORKER_RESTARTED=true" in output, output
    assert "CONSUMER_RESTARTED=true" in output, output
    assert "SCHEDULER_RESTARTED=true" in output, output
    assert "COMPLETED=[job_alpha,{crash_once,batch_beta},job_gamma]" in output, output
    assert "PENDING=[]" in output, output
    assert "LEASES=#{}" in output, output


def test_pipeline_keeps_throughput_after_recovery() -> None:
    expr = textwrap.dedent(
        """
        {ok, SupPid} = pipeline_sup:start_link(),
        unlink(SupPid),
        ok = pipeline_queue:enqueue({crash_once, batch_one}),
        ok = pipeline_queue:enqueue(job_two),
        WaitCompleted =
            fun Self(0) ->
                    erlang:error({timeout, pipeline_queue:snapshot()});
                Self(AttemptsLeft) ->
                    case maps:get(completed, pipeline_queue:snapshot()) of
                        [{crash_once, batch_one}, job_two] ->
                            ok;
                        _ ->
                            timer:sleep(40),
                            Self(AttemptsLeft - 1)
                    end
            end,
        ok = WaitCompleted(100),
        ok = pipeline_queue:enqueue(job_three),
        WaitExtended =
            fun Self(0) ->
                    erlang:error({timeout, pipeline_queue:snapshot()});
                Self(AttemptsLeft) ->
                    case maps:get(completed, pipeline_queue:snapshot()) of
                        [{crash_once, batch_one}, job_two, job_three] ->
                            ok;
                        _ ->
                            timer:sleep(40),
                            Self(AttemptsLeft - 1)
                    end
            end,
        ok = WaitExtended(100),
        Snapshot = pipeline_queue:snapshot(),
        io:format(
            "SUP_ALIVE=~p~nFINAL_COMPLETED=~p~nPENDING=~p~nLEASES=~p~n",
            [
                erlang:is_process_alive(SupPid),
                maps:get(completed, Snapshot),
                maps:get(pending, Snapshot),
                maps:get(leases, Snapshot)
            ]
        ),
        exit(SupPid, shutdown).
        """
    ).strip()

    output = _erl_eval(expr)

    assert "SUP_ALIVE=true" in output, output
    assert "FINAL_COMPLETED=[{crash_once,batch_one},job_two,job_three]" in output, output
    assert "PENDING=[]" in output, output
    assert "LEASES=#{}" in output, output
