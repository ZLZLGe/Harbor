import {
  commitEventConfirmation,
  fetchApprovalQueue,
  fetchConfirmationDraft,
  fetchDeploymentLane,
  fetchIncidentFeed,
  fetchOperatorSession,
  fetchPolicyPack,
  fetchServiceHealth,
  logEventConfirmation,
  type ApprovalItem,
  type ConfirmationResult,
  type DeploymentItem,
  type IncidentItem,
  type OperatorSession,
  type ServiceHealthItem,
} from './controlRoomApi';

export interface ControlRoomData {
  operator: OperatorSession;
  incidentFeed: IncidentItem[];
  serviceHealth: ServiceHealthItem[];
  deploymentLane: DeploymentItem[];
  approvals: ApprovalItem[];
}

export interface ConfirmedEventPayload {
  eventId: string;
  status: ConfirmationResult['status'];
  confirmedBy: string;
  runbookId: string;
  timelineMessage: string;
}

async function getFreshSession() {
  return fetchOperatorSession();
}

export async function getControlRoomData(): Promise<ControlRoomData> {
  const incidentFeed = await fetchIncidentFeed((await getFreshSession()).token);
  const serviceHealth = await fetchServiceHealth((await getFreshSession()).token);
  const deploymentLane = await fetchDeploymentLane((await getFreshSession()).token);
  const approvals = await fetchApprovalQueue((await getFreshSession()).token);
  const operator = await getFreshSession();

  return {
    operator,
    incidentFeed,
    serviceHealth,
    deploymentLane,
    approvals,
  };
}

export async function confirmControlRoomEvent(eventId: string): Promise<ConfirmedEventPayload> {
  const operator = await fetchOperatorSession();
  const policy = await fetchPolicyPack(eventId, operator.token);
  const confirmationDraft = await fetchConfirmationDraft(eventId, operator.token);
  const confirmed = await commitEventConfirmation(
    eventId,
    operator.token,
    confirmationDraft.confirmationId,
    policy.runbookId,
  );

  await logEventConfirmation({
    eventId,
    operatorId: operator.operatorId,
    confirmationId: confirmationDraft.confirmationId,
    status: confirmed.status,
  });

  return {
    eventId: confirmed.eventId,
    status: confirmed.status,
    confirmedBy: operator.displayName,
    runbookId: policy.runbookId,
    timelineMessage: `${confirmed.eventId} acknowledged by ${operator.displayName}`,
  };
}
