-module(pipeline_scheduler).
-behaviour(gen_server).

-export([start_link/0]).
-export([init/1, handle_info/2, terminate/2, code_change/3]).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

init([]) ->
    case whereis(pipeline_consumer) of
        undefined ->
            {stop, consumer_not_ready};
        ConsumerPid ->
            erlang:send_after(0, self(), tick),
            {ok, #{consumer_pid => ConsumerPid, interval_ms => 25}}
    end.

handle_info(tick, State = #{consumer_pid := ConsumerPid, interval_ms := IntervalMs}) ->
    ConsumerPid ! dispatch,
    erlang:send_after(IntervalMs, self(), tick),
    {noreply, State};
handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.
