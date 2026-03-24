export type WorkspaceView = 'overview' | 'activity' | 'alerts';

export type ActivitySeverity = 'healthy' | 'watch' | 'critical';

export interface ActivityRecord {
  id: string;
  pipeline: string;
  owner: string;
  severity: ActivitySeverity;
  latencyMs: number;
  queueDepth: number;
  region: string;
  summary: string;
}

const owners = ['Nora', 'Darius', 'Mei', 'Harper', 'Luis', 'Aisha'];
const regions = ['us-east', 'us-west', 'eu-central', 'ap-south'];
const pipelines = ['stream', 'warehouse', 'campaign', 'billing', 'retention', 'risk'];

export const ACTIVITY_FEED: ActivityRecord[] = Array.from({ length: 240 }, (_, index) => {
  const pipeline = pipelines[index % pipelines.length];
  const severityIndex = index % 9;
  const severity: ActivitySeverity =
    severityIndex === 0 ? 'critical' : severityIndex < 4 ? 'watch' : 'healthy';

  return {
    id: `stream-${String(index + 1).padStart(3, '0')}`,
    pipeline,
    owner: owners[index % owners.length],
    severity,
    latencyMs: 95 + (index % 11) * 18 + Math.floor(index / 12) * 7,
    queueDepth: 14 + (index % 8) * 6 + Math.floor(index / 15) * 4,
    region: regions[index % regions.length],
    summary: `${pipeline} drift review #${index + 1}`,
  };
});

export function rowsForView(view: WorkspaceView) {
  if (view === 'overview') {
    return ACTIVITY_FEED.slice(0, 8);
  }

  if (view === 'alerts') {
    return ACTIVITY_FEED.filter((row) => row.severity === 'critical').slice(0, 14);
  }

  return ACTIVITY_FEED;
}
