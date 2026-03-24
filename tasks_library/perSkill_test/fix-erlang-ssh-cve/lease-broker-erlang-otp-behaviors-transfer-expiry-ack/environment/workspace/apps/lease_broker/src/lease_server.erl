-module(lease_server).
-behaviour(gen_server).

-export([
    start_link/3,
    checkout/2,
    confirm/3,
    renew/2,
    release/3,
    status/1,
    stop/1
]).

-export([
    init/1,
    handle_call/3,
    handle_cast/2,
    handle_info/2,
    terminate/2,
    code_change/3
]).

-record(lease, {
    lease_id,
    client_id,
    resource,
    phase = awaiting_confirm,
    confirm_ref = undefined,
    expiry_ref = undefined
}).

-record(state, {
    order = [],
    resources = #{},
    leases = #{},
    confirm_ms = 80,
    lease_ms = 160,
    next_lease_id = 1
}).

start_link(Resources, ConfirmMs, LeaseMs) ->
    gen_server:start_link(?MODULE, [Resources, ConfirmMs, LeaseMs], []).

checkout(Pid, ClientId) ->
    gen_server:call(Pid, {checkout, ClientId}).

confirm(Pid, LeaseId, Resource) ->
    gen_server:cast(Pid, {confirm, LeaseId, Resource}).

renew(Pid, LeaseId) ->
    gen_server:call(Pid, {renew, LeaseId}).

release(Pid, LeaseId, Resource) ->
    gen_server:cast(Pid, {release, LeaseId, Resource}).

status(Pid) ->
    gen_server:call(Pid, status).

stop(Pid) ->
    gen_server:call(Pid, stop).

init([Resources, ConfirmMs, LeaseMs]) ->
    ResourceMap = maps:from_list([{Resource, free} || Resource <- Resources]),
    {ok, #state{
        order = Resources,
        resources = ResourceMap,
        confirm_ms = ConfirmMs,
        lease_ms = LeaseMs
    }}.

handle_call({checkout, ClientId}, _From, State = #state{
    order = Order,
    resources = Resources,
    leases = Leases,
    confirm_ms = ConfirmMs,
    next_lease_id = LeaseId
}) ->
    case first_free(Order, Resources) of
        {ok, Resource} ->
            ConfirmRef = erlang:start_timer(ConfirmMs, self(), {confirm_timeout, LeaseId}),
            Lease = #lease{
                lease_id = LeaseId,
                client_id = ClientId,
                resource = Resource,
                confirm_ref = ConfirmRef
            },
            {reply, {ok, LeaseId, Resource}, State#state{
                resources = maps:put(Resource, {pending, LeaseId}, Resources),
                leases = maps:put(LeaseId, Lease, Leases),
                next_lease_id = LeaseId + 1
            }};
        none ->
            {reply, {error, unavailable}, State}
    end;
handle_call({renew, LeaseId}, _From, State = #state{leases = Leases, lease_ms = LeaseMs}) ->
    case maps:find(LeaseId, Leases) of
        {ok, Lease = #lease{phase = active}} ->
            ExpiryRef = erlang:start_timer(LeaseMs, self(), {lease_expired, LeaseId}),
            UpdatedLease = Lease#lease{expiry_ref = ExpiryRef},
            {reply, ok, State#state{leases = maps:put(LeaseId, UpdatedLease, Leases)}};
        {ok, _Lease} ->
            {reply, {error, not_active}, State};
        error ->
            {reply, {error, unknown_lease}, State}
    end;
handle_call(status, _From, State) ->
    {reply, snapshot(State), State};
handle_call(stop, _From, State) ->
    {stop, normal, ok, State};
handle_call(_Request, _From, State) ->
    {reply, {error, unknown_call}, State}.

handle_cast({confirm, LeaseId, Resource}, State = #state{
    resources = Resources,
    leases = Leases,
    lease_ms = LeaseMs
}) ->
    case maps:find(LeaseId, Leases) of
        {ok, Lease = #lease{
            resource = Resource,
            phase = awaiting_confirm,
            confirm_ref = ConfirmRef
        }} ->
            maybe_cancel_timer(ConfirmRef),
            ExpiryRef = erlang:start_timer(LeaseMs, self(), {lease_expired, LeaseId}),
            UpdatedLease = Lease#lease{
                phase = active,
                confirm_ref = undefined,
                expiry_ref = ExpiryRef
            },
            {noreply, State#state{
                resources = maps:put(Resource, {active, LeaseId}, Resources),
                leases = maps:put(LeaseId, UpdatedLease, Leases)
            }};
        error ->
            {noreply, State#state{
                resources = maps:put(Resource, {active, LeaseId}, Resources)
            }};
        _ ->
            {noreply, State}
    end;
handle_cast({release, LeaseId, Resource}, State = #state{resources = Resources, leases = Leases}) ->
    case maps:take(LeaseId, Leases) of
        {#lease{
            resource = Resource,
            confirm_ref = ConfirmRef,
            expiry_ref = ExpiryRef
        }, RemainingLeases} ->
            maybe_cancel_timer(ConfirmRef),
            maybe_cancel_timer(ExpiryRef),
            {noreply, State#state{
                resources = maps:put(Resource, free, Resources),
                leases = RemainingLeases
            }};
        error ->
            {noreply, State#state{
                resources = maps:put(Resource, {held, LeaseId}, Resources)
            }};
        _ ->
            {noreply, State}
    end;
handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info({timeout, _Ref, {confirm_timeout, LeaseId}}, State = #state{
    resources = Resources,
    leases = Leases
}) ->
    case maps:find(LeaseId, Leases) of
        {ok, #lease{resource = Resource, phase = awaiting_confirm}} ->
            {Lease, RemainingLeases} = maps:take(LeaseId, Leases),
            maybe_cancel_timer(Lease#lease.confirm_ref),
            {noreply, State#state{
                resources = maps:put(Resource, free, Resources),
                leases = RemainingLeases
            }};
        _ ->
            {noreply, State}
    end;
handle_info({timeout, _Ref, {lease_expired, LeaseId}}, State = #state{
    resources = Resources,
    leases = Leases
}) ->
    case maps:take(LeaseId, Leases) of
        {#lease{resource = Resource}, RemainingLeases} ->
            {noreply, State#state{
                resources = maps:put(Resource, free, Resources),
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

maybe_cancel_timer(undefined) ->
    ok;
maybe_cancel_timer(Ref) ->
    erlang:cancel_timer(Ref),
    ok.

first_free([], _Resources) ->
    none;
first_free([Resource | Rest], Resources) ->
    case maps:get(Resource, Resources, free) of
        free ->
            {ok, Resource};
        _ ->
            first_free(Rest, Resources)
    end.

snapshot(#state{resources = Resources, leases = Leases, next_lease_id = NextLeaseId}) ->
    #{
        resources => Resources,
        leases => maps:from_list([
            {LeaseId, #{
                client_id => Lease#lease.client_id,
                resource => Lease#lease.resource,
                phase => Lease#lease.phase
            }}
            || {LeaseId, Lease} <- maps:to_list(Leases)
        ]),
        next_lease_id => NextLeaseId
    }.
