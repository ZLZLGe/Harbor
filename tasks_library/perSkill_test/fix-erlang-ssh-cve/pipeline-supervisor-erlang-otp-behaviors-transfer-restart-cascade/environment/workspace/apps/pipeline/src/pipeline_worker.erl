-module(pipeline_worker).
-behaviour(gen_server).

-export([start_link/0, process/2]).
-export([init/1, handle_call/3, terminate/2, code_change/3]).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

process(Pid, Job) ->
    gen_server:call(Pid, {process, Job}, 5000).

init([]) ->
    {ok, #{}}.

handle_call({process, {crash_once, Name}}, _From, State) ->
    Key = {?MODULE, crash_once, Name},
    case persistent_term:get(Key, false) of
        false ->
            persistent_term:put(Key, true),
            exit(simulated_worker_crash);
        true ->
            {reply, ok, State}
    end;
handle_call({process, _Job}, _From, State) ->
    {reply, ok, State};
handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.
