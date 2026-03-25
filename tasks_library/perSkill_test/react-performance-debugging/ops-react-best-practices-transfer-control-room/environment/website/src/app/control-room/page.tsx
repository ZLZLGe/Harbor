import { getControlRoomData } from '@/lib/getControlRoomData';

export const dynamic = 'force-dynamic';

export default async function ControlRoomPage() {
  const data = await getControlRoomData();

  return (
    <main className="page-shell">
      <header className="hero">
        <div>
          <h1>Regional Control Room</h1>
          <p>Live operational posture for the next escalation window.</p>
        </div>
        <div data-testid="operator-chip" className="operator-chip">
          {data.operator.displayName} · {data.operator.region}
        </div>
      </header>

      <div className="grid">
        <section data-testid="incident-feed" className="panel">
          <h2>Incident feed</h2>
          <ul>
            {data.incidentFeed.map((incident) => (
              <li key={incident.incidentId}>
                <strong>{incident.title}</strong>
                <div className="meta">
                  {incident.service} · ETA {incident.eta}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section data-testid="service-health" className="panel">
          <h2>Service health</h2>
          <ul>
            {data.serviceHealth.map((service) => (
              <li key={service.service}>
                <strong>{service.service}</strong>
                <div className="meta">
                  {service.status} · {service.saturation}% saturation
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section data-testid="deployment-lane" className="panel">
          <h2>Deployment lane</h2>
          <ul>
            {data.deploymentLane.map((deployment) => (
              <li key={deployment.train}>
                <strong>{deployment.train}</strong>
                <div className="meta">
                  {deployment.window} · owner {deployment.owner}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section data-testid="approval-queue" className="panel">
          <h2>Approval queue</h2>
          <ul>
            {data.approvals.map((approval) => (
              <li key={approval.eventId}>
                <strong>{approval.eventId}</strong>
                <div className="meta">
                  {approval.service} · {approval.summary}
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}
