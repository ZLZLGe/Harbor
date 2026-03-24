import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


WORKSPACE = Path("/app/workspace")
SOURCE_FILE = WORKSPACE / "apps" / "lease_broker" / "src" / "lease_server.erl"
EBIN_DIR = Path("/tmp/lease-broker-ebin")


def _run(cmd: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout
    )


def _compile_module() -> None:
    shutil.rmtree(EBIN_DIR, ignore_errors=True)
    EBIN_DIR.mkdir(parents=True, exist_ok=True)
    proc = _run(["erlc", "-o", str(EBIN_DIR), str(SOURCE_FILE)])
    assert proc.returncode == 0, (
        "failed to compile lease_server.erl\n"
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
        ]
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
    assert SOURCE_FILE.exists(), f"missing source file: {SOURCE_FILE}"
    _compile_module()


def test_expired_confirm_is_ignored() -> None:
    expr = textwrap.dedent(
        """
        {ok, Pid} = lease_server:start_link([slot_a], 50, 160),
        {ok, LeaseId, slot_a} = lease_server:checkout(Pid, client_a),
        timer:sleep(120),
        lease_server:confirm(Pid, LeaseId, slot_a),
        timer:sleep(30),
        Second = lease_server:checkout(Pid, client_b),
        Status = lease_server:status(Pid),
        Resources = maps:get(resources, Status),
        io:format("SECOND=~p~nRESOURCE=~p~n", [
            Second,
            maps:get(slot_a, Resources)
        ]).
        """
    ).strip()

    output = _erl_eval(expr)

    assert "SECOND={ok,2,slot_a}" in output, output
    assert "RESOURCE={pending,2}" in output, output


def test_expired_release_is_ignored() -> None:
    expr = textwrap.dedent(
        """
        {ok, Pid} = lease_server:start_link([slot_a], 50, 160),
        {ok, LeaseId, slot_a} = lease_server:checkout(Pid, client_a),
        timer:sleep(120),
        lease_server:release(Pid, LeaseId, slot_a),
        timer:sleep(30),
        Second = lease_server:checkout(Pid, client_b),
        Status = lease_server:status(Pid),
        Resources = maps:get(resources, Status),
        io:format("SECOND=~p~nRESOURCE=~p~n", [
            Second,
            maps:get(slot_a, Resources)
        ]).
        """
    ).strip()

    output = _erl_eval(expr)

    assert "SECOND={ok,2,slot_a}" in output, output
    assert "RESOURCE={pending,2}" in output, output


def test_renew_replaces_old_expiry_timer() -> None:
    expr = textwrap.dedent(
        """
        {ok, Pid} = lease_server:start_link([slot_a], 50, 160),
        {ok, LeaseId, slot_a} = lease_server:checkout(Pid, client_a),
        lease_server:confirm(Pid, LeaseId, slot_a),
        timer:sleep(90),
        Renew = lease_server:renew(Pid, LeaseId),
        timer:sleep(110),
        MidStatus = lease_server:status(Pid),
        MidResources = maps:get(resources, MidStatus),
        MidCheckout = lease_server:checkout(Pid, client_b),
        timer:sleep(90),
        FinalCheckout = lease_server:checkout(Pid, client_c),
        io:format("RENEW=~p~nMID_RESOURCE=~p~nMID_CHECKOUT=~p~nFINAL_CHECKOUT=~p~n", [
            Renew,
            maps:get(slot_a, MidResources),
            MidCheckout,
            FinalCheckout
        ]).
        """
    ).strip()

    output = _erl_eval(expr)

    assert "RENEW=ok" in output, output
    assert "MID_RESOURCE={active,1}" in output, output
    assert "MID_CHECKOUT={error,unavailable}" in output, output
    assert "FINAL_CHECKOUT={ok,2,slot_a}" in output, output


def test_normal_confirm_renew_release_flow() -> None:
    expr = textwrap.dedent(
        """
        {ok, Pid} = lease_server:start_link([slot_a], 50, 180),
        {ok, LeaseId, slot_a} = lease_server:checkout(Pid, client_a),
        lease_server:confirm(Pid, LeaseId, slot_a),
        timer:sleep(20),
        Renew = lease_server:renew(Pid, LeaseId),
        lease_server:release(Pid, LeaseId, slot_a),
        timer:sleep(30),
        Second = lease_server:checkout(Pid, client_b),
        Status = lease_server:status(Pid),
        Resources = maps:get(resources, Status),
        io:format("RENEW=~p~nSECOND=~p~nRESOURCE=~p~n", [
            Renew,
            Second,
            maps:get(slot_a, Resources)
        ]).
        """
    ).strip()

    output = _erl_eval(expr)

    assert "RENEW=ok" in output, output
    assert "SECOND={ok,2,slot_a}" in output, output
    assert "RESOURCE={pending,2}" in output, output
