#!/bin/bash
set -e

cd /app

python3 - <<'PY'
from pathlib import Path

path = Path("src/lib/getControlRoomData.ts")
text = path.read_text()

replacements = [
    (
        "import {\n",
        "import { cache } from 'react';\n\nimport {\n",
    ),
    (
        "async function getFreshSession() {\n  return fetchOperatorSession();\n}\n",
        "const getOperatorSession = cache(async () => fetchOperatorSession());\n",
    ),
    (
        """export async function getControlRoomData(): Promise<ControlRoomData> {\n  const incidentFeed = await fetchIncidentFeed((await getFreshSession()).token);\n  const serviceHealth = await fetchServiceHealth((await getFreshSession()).token);\n  const deploymentLane = await fetchDeploymentLane((await getFreshSession()).token);\n  const approvals = await fetchApprovalQueue((await getFreshSession()).token);\n  const operator = await getFreshSession();\n\n  return {\n    operator,\n    incidentFeed,\n    serviceHealth,\n    deploymentLane,\n    approvals,\n  };\n}\n""",
        """export async function getControlRoomData(): Promise<ControlRoomData> {\n  const operator = await getOperatorSession();\n\n  const [incidentFeed, serviceHealth, deploymentLane, approvals] = await Promise.all([\n    fetchIncidentFeed(operator.token),\n    fetchServiceHealth(operator.token),\n    fetchDeploymentLane(operator.token),\n    fetchApprovalQueue(operator.token),\n  ]);\n\n  return {\n    operator,\n    incidentFeed,\n    serviceHealth,\n    deploymentLane,\n    approvals,\n  };\n}\n""",
    ),
    (
        """export async function confirmControlRoomEvent(eventId: string): Promise<ConfirmedEventPayload> {\n  const operator = await fetchOperatorSession();\n  const policy = await fetchPolicyPack(eventId, operator.token);\n  const confirmationDraft = await fetchConfirmationDraft(eventId, operator.token);\n  const confirmed = await commitEventConfirmation(\n    eventId,\n    operator.token,\n    confirmationDraft.confirmationId,\n    policy.runbookId,\n  );\n\n  await logEventConfirmation({\n    eventId,\n    operatorId: operator.operatorId,\n    confirmationId: confirmationDraft.confirmationId,\n    status: confirmed.status,\n  });\n\n  return {\n    eventId: confirmed.eventId,\n    status: confirmed.status,\n    confirmedBy: operator.displayName,\n    runbookId: policy.runbookId,\n    timelineMessage: `${confirmed.eventId} acknowledged by ${operator.displayName}`,\n  };\n}\n""",
        """export async function confirmControlRoomEvent(eventId: string): Promise<ConfirmedEventPayload> {\n  const operatorPromise = getOperatorSession();\n  const policyPromise = operatorPromise.then((operator) => fetchPolicyPack(eventId, operator.token));\n  const confirmationDraftPromise = operatorPromise.then((operator) =>\n    fetchConfirmationDraft(eventId, operator.token),\n  );\n\n  const [operator, policy, confirmationDraft] = await Promise.all([\n    operatorPromise,\n    policyPromise,\n    confirmationDraftPromise,\n  ]);\n\n  const confirmed = await commitEventConfirmation(\n    eventId,\n    operator.token,\n    confirmationDraft.confirmationId,\n    policy.runbookId,\n  );\n\n  void logEventConfirmation({\n    eventId,\n    operatorId: operator.operatorId,\n    confirmationId: confirmationDraft.confirmationId,\n    status: confirmed.status,\n  });\n\n  return {\n    eventId: confirmed.eventId,\n    status: confirmed.status,\n    confirmedBy: operator.displayName,\n    runbookId: policy.runbookId,\n    timelineMessage: `${confirmed.eventId} acknowledged by ${operator.displayName}`,\n  };\n}\n""",
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"expected snippet not found:\\n{old}")
    text = text.replace(old, new, 1)

path.write_text(text)
PY

npm run build >/tmp/control-room-build.log 2>&1
