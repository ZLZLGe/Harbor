-module(pipeline_queue).
-behaviour(gen_server).

-export([start_link/0, enqueue/1, reserve/1, ack/1, snapshot/0]).
-export([init/1, handle_call/3, handle_info/2, terminate/2, code_change/3]).

-record(state, {
    pending = [],
    leases = #{},
    completed = []
}).

start_link() ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).

enqueue(Job) ->
    gen_server:call(?MODULE, {enqueue, Job}).

reserve(ConsumerPid) ->
    gen_server:call(?MODULE, {reserve, ConsumerPid}).

ack(LeaseId) ->
    gen_server:call(?MODULE, {ack, LeaseId}).

snapshot() ->
    gen_server:call(?MODULE, snapshot).

init([]) ->
    {ok, #state{}}.

handle_call({enqueue, Job}, _From, State = #state{pending = Pending}) ->
    {reply, ok, State#state{pending = Pending ++ [Job]}};
handle_call({reserve, ConsumerPid}, _From, State = #state{pending = []}) ->
    {reply, empty, State};
handle_call({reserve, ConsumerPid}, _From, State = #state{pending = [Job | Rest], leases = Leases}) ->
    LeaseId = erlang:unique_integer([positive]),
    MonitorRef = erlang:monitor(process, ConsumerPid),
    Lease = #{job => Job, consumer => ConsumerPid, monitor => MonitorRef},
    {reply, {ok, LeaseId, Job}, State#state{
        pending = Rest,
        leases = maps:put(LeaseId, Lease, Leases)
    }};
handle_call({ack, LeaseId}, _From, State = #state{leases = Leases, completed = Completed}) ->
    case maps:take(LeaseId, Leases) of
        {#{job := Job, monitor := MonitorRef}, RemainingLeases} ->
            erlang:demonitor(MonitorRef, [flush]),
            {reply, ok, State#state{
                leases = RemainingLeases,
                completed = Completed ++ [Job]
            }};
        error ->
            {reply, {error, unknown_lease}, State}
    end;
handle_call(snapshot, _From, State = #state{pending = Pending, leases = Leases, completed = Completed}) ->
    LeaseSummary = maps:from_list([
        {LeaseId, maps:with([job, consumer], Lease)}
        || {LeaseId, Lease} <- maps:to_list(Leases)
    ]),
    {reply, #{
        pending => Pending,
        leases => LeaseSummary,
        completed => Completed
    }, State};
handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_info({'DOWN', MonitorRef, process, _Pid, _Reason}, State = #state{
    pending = Pending,
    leases = Leases
}) ->
    case take_lease_by_monitor(MonitorRef, Leases) of
        {ok, _LeaseId, #{job := Job}, RemainingLeases} ->
            {noreply, State#state{
                pending = [Job | Pending],
                leases = RemainingLeases
            }};
        error ->
            {noreply, State}
    end;
handle_info(_Info, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

take_lease_by_monitor(MonitorRef, Leases) ->
    Matches = [
        {LeaseId, Lease}
        || {LeaseId, Lease = #{monitor := Ref}} <- maps:to_list(Leases),
           Ref =:= MonitorRef
    ],
    case Matches of
        [{LeaseId, Lease}] ->
            {ok, LeaseId, Lease, maps:remove(LeaseId, Leases)};
        [] ->
            error
    end.
