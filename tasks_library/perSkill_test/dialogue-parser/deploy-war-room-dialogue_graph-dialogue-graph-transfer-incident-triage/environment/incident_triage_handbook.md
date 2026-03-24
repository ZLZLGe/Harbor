# Release War Room Handbook

Use this handbook only after a deployment-related alert has triggered.
Ignore the prose lines above and below when building the graph.

- Treat `End` as the terminal sink for concluded incidents.
- Bracketed tags such as `[Rollback]` or `[Vendor Escalation]` are part of the option text.

[AlertIngress]
Monitor: PagerDuty reports elevated 5xx after the 09:40 deploy wave. -> SeverityGate

[SeverityGate]
1. [SEV-1] Error rate is above 20% or checkout is fully down. -> SevOneBridge
2. Error rate is elevated but core transactions still succeed. -> SevTwoAssess
3. Alert appears noisy or is already recovering. -> MonitorNoiseReview

[SevOneBridge]
IncidentLead: Open the release war room, assign an incident scribe, and confirm customer impact within five minutes. -> BlastRadiusChoice

[BlastRadiusChoice]
1. [Rollback] Symptoms started immediately after the latest deploy. -> RollbackPrep
2. [Dependency] Traces point to a gateway, cache, or database dependency. -> DependencyCheck
3. [Comms] Support volume is spiking and a status update may be needed. -> StatusDraft

[RollbackPrep]
ReleaseEngineer: Compare the failing build to the last healthy release and confirm which switch is safest to reverse first. -> RollbackChoice

[RollbackChoice]
1. [Feature Flag] Disable the new feature flag before touching the build. -> FlagDisable
2. Start a full application rollback. -> RollbackExecute
3. Ask the database owner whether schema changes block a rollback. -> DatabaseCheck

[FlagDisable]
ReleaseEngineer: The feature flag is disabled and the newest requests are draining through the old path. -> StabilizationReview

[RollbackExecute]
ReleaseEngineer: The previous release is redeploying across the production cluster now. -> StabilizationReview

[DatabaseCheck]
Database: I am checking replica lag, lock contention, and whether the new schema can safely move backward. -> DatabaseChoice

[DatabaseChoice]
1. [DB Failover] Lag or lock contention is severe enough to move traffic. -> FailoverStep
2. The schema is backward-compatible, so application rollback is safe. -> RollbackExecute
3. We need a specialist on the bridge before changing anything. -> ManualMitigationHandoff

[FailoverStep]
Database: Promote the healthy replica, pin writes there, and let the old primary cool down. -> StabilizationReview

[StatusDraft]
Comms: I have a draft customer update and can publish it as soon as we agree on scope and wording. -> StatusChoice

[StatusChoice]
1. Publish the customer-facing note and continue dependency triage. -> DependencyCheck
2. Send an internal-only heads-up and continue rollback preparation. -> RollbackPrep
3. Metrics are already improving, so defer the update and re-check stability. -> StabilizationReview

[DependencyCheck]
SRE: Compare trace spans, dependency dashboards, and deploy timing to find out whether the fault sits outside the application pods. -> DependencyChoice

[DependencyChoice]
1. [Vendor Escalation] A third-party API latency spike dominates the traces. -> VendorBridge
2. [Cache Flush] Stale configuration or cache data is serving bad responses. -> CacheMitigation
3. Edge traffic shifted unevenly after the deploy. -> EdgeBalancerCheck
4. No external signal stands out, return to the rollback path. -> RollbackPrep

[VendorBridge]
SRE: The vendor bridge is open, and their engineer wants either degraded mode or a five-minute observation window. -> VendorChoice

[VendorChoice]
1. Enable degraded mode while the vendor works the incident. -> DegradedMode
2. Wait five minutes and then repeat dependency checks. -> DependencyCheck

[DegradedMode]
SRE: Degraded mode is on, error volume has dropped, and we can check whether the customer-facing path is stable enough to hold. -> StabilizationReview

[CacheMitigation]
SRE: Flush the stale cache tier, reload configuration, and watch whether the failing requests clear. -> StabilizationReview

[EdgeBalancerCheck]
EdgeTeam: One region is receiving a bad slice of traffic while the rest of the edge looks healthy. -> EdgeChoice

[EdgeChoice]
1. Drain the unhealthy zone and keep the remaining regions serving traffic. -> ZoneDrain
2. Revert the canary routing weights to the previous distribution. -> RoutingRevert
3. Escalate the imbalance to the platform war room. -> PlatformEscalation

[ZoneDrain]
EdgeTeam: The unhealthy zone is drained and user traffic has shifted to the remaining regions. -> StabilizationReview

[RoutingRevert]
EdgeTeam: Canary routing weights are back to the pre-deploy split. -> StabilizationReview

[PlatformEscalation]
IncidentLead: Platform engineering is taking over the live mitigation while we preserve notes and customer timelines. -> ManualMitigationHandoff

[SevTwoAssess]
IncidentLead: Keep the release bridge small, assign one owner per hypothesis, and confirm whether the incident is user-visible before escalating. -> ServiceCheckChoice

[ServiceCheckChoice]
1. [Logs] Errors cluster around one service or endpoint. -> ServiceOwnerCheck
2. [Capacity] CPU, memory, or queue depth spiked after rollout. -> CapacityPlan
3. The issue is quiet for customers but persistent in alerts. -> SlowBurnDecision

[ServiceOwnerCheck]
ServiceOwner: I checked the newest pods, recent endpoint changes, and the top failing requests in the service logs. -> ServiceOwnerChoice

[ServiceOwnerChoice]
1. Restart only the newest pods and keep the rest of the deployment. -> RestartPods
2. Disable the new endpoint behind a feature flag. -> FlagDisable
3. Escalate this to the SEV-1 bridge now. -> SevOneBridge

[RestartPods]
ServiceOwner: The newest pods are restarting, and the previous replicas are still serving traffic. -> StabilizationReview

[CapacityPlan]
SRE: Queue depth and worker saturation are the clearest signals, so capacity relief is the fastest next move. -> CapacityChoice

[CapacityChoice]
1. Scale out the workers and web pods. -> ScaleOut
2. [Queue Drain] Pause noncritical jobs and drain the backlog first. -> QueueDrain
3. Capacity looks secondary, so inspect dependencies instead. -> DependencyCheck

[ScaleOut]
SRE: Extra capacity is online and the backlog is shrinking. -> StabilizationReview

[QueueDrain]
SRE: Noncritical jobs are paused, the backlog is draining, and the hot path has more headroom. -> StabilizationReview

[SlowBurnDecision]
SupportLead: Customer reports are sparse, but the error budget is burning steadily enough that we may still need to widen the response. -> SlowBurnChoice

[SlowBurnChoice]
1. Draft an internal advisory and keep watching the metrics. -> WatchWindow
2. Escalate to SEV-1 because the burn rate is accelerating. -> SevOneBridge
3. Verify whether this is only monitor noise. -> MonitorNoiseReview

[WatchWindow]
Monitor: Hold a ten-minute watch window and compare live traffic, error budget burn, and support chatter before changing mitigation. -> WatchChoice

[WatchChoice]
1. Metrics recover during the watch window without another action. -> FalseAlarmClosed
2. Metrics worsen and customer errors start climbing fast. -> SevOneBridge
3. One service keeps failing, so continue service-level checks. -> ServiceOwnerCheck

[MonitorNoiseReview]
Observability: Check whether the alert came from a synthetic probe, a silenced canary, or a query that changed labels during the deploy. -> NoiseChoice

[NoiseChoice]
1. The alert only fired from a synthetic probe or silenced canary. -> FalseAlarmClosed
2. The alert query is wrong after a label or dashboard change. -> QueryFix
3. We still see uncertain impact, so return to SEV-2 assessment. -> SevTwoAssess

[QueryFix]
Observability: The alert rule is corrected and historical data confirms that production traffic stayed healthy. -> FalseAlarmClosed

[StabilizationReview]
IncidentLead: Re-check the core user journey, watch the main dashboards for fifteen minutes, and decide whether the incident is stable enough to close. -> StabilizationChoice

[StabilizationChoice]
1. Metrics are back to baseline and the user journey is healthy. -> RecoverySummary
2. Error rate improved but is not stable enough yet. -> BridgeRecheck
3. A second region or service is now impacted. -> SevOneBridge

[BridgeRecheck]
IncidentLead: Choose the next review loop based on which hypothesis is still alive after the latest mitigation. -> BridgeChoice

[BridgeChoice]
1. Re-run the service-level checks. -> ServiceCheckChoice
2. Re-run the dependency checks. -> DependencyCheck
3. Prepare a manual handoff to the overnight or platform team. -> ManualMitigationHandoff

[RecoverySummary]
Comms: The incident looks stable, so choose the summary that best matches the mitigation we used and close the loop cleanly. -> RecoveryChoice

[RecoveryChoice]
1. Close this as a rollback recovery. -> RollbackComplete
2. Close this as a capacity recovery. -> CapacityRecovered
3. Close this as a dependency mitigation. -> DependencyMitigated
4. Close this as a feature-flag mitigation. -> FeatureFlagRecovered

[FalseAlarmClosed]
Observability: Close the incident as monitor noise or a self-recovered alert, and attach the query notes for follow-up tuning. -> End

[RollbackComplete]
Comms: Rollback recovery confirmed, customer traffic is healthy, and the release can stay frozen pending review. -> End

[CapacityRecovered]
IncidentLead: Capacity mitigation held through the watch window, so we can close and schedule scaling follow-up. -> End

[DependencyMitigated]
SRE: Dependency mitigation is holding, with degraded mode or routing changes documented for the next review. -> End

[FeatureFlagRecovered]
ReleaseEngineer: The feature flag rollback restored stability, and the launch stays disabled until the fix is ready. -> End

[ManualMitigationHandoff]
IncidentLead: Hand off the active mitigation to the next team with timeline, open hypotheses, and customer impact notes attached. -> End
