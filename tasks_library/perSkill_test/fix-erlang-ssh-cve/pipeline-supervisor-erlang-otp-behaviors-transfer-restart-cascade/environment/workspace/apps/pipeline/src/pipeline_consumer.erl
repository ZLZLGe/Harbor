-module(pipeline_consumer).
-behaviour(gen_server).

-export([start_link/0]).
-export([init/1, handle_info/2, terminate/2, code_change/3]).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

init([]) ->
    case whereis(pipeline_worker) of
        undefined ->
            {stop, worker_not_ready};
        WorkerPid ->
            {ok, #{worker_pid => WorkerPid}}
    end.

handle_info(dispatch, State = #{worker_pid := WorkerPid}) ->
    case pipeline_queue:reserve(self()) of
        empty ->
            {noreply, State};
        {ok, LeaseId, Job} ->
            ok = pipeline_worker:process(WorkerPid, Job),
            ok = pipeline_queue:ack(LeaseId),
            {noreply, State}
    end;
handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.
