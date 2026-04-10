export interface DashboardSummary {
  revenueToday: number;
  activeAlerts: number;
  conversionDelta: number;
}

export interface DashboardFilter {
  id: string;
  label: string;
  teaser: string;
}

export interface DashboardAlert {
  id: string;
  title: string;
  filterId: string;
  severity: 'high' | 'medium' | 'low';
  owner: string;
  impactDelta: number;
  summary: string;
}

export interface TimelinePoint {
  id: string;
  filterId: string;
  day: string;
  sessions: number;
  conversionRate: number;
  revenueK: number;
}

export interface DashboardSnapshot {
  snapshotId: string;
  summary: DashboardSummary;
  filters: DashboardFilter[];
  alerts: DashboardAlert[];
  timeline: TimelinePoint[];
}

export const DEFAULT_FILTER = 'all-regions';

export function findFilter(filters: DashboardFilter[], filterId: string): DashboardFilter {
  return filters.find((filter) => filter.id === filterId) ?? filters[0];
}

export function filterAlerts(alerts: DashboardAlert[], filterId: string) {
  if (filterId === DEFAULT_FILTER) {
    return alerts;
  }
  return alerts.filter((alert) => alert.filterId === filterId);
}

export function filterTimeline(points: TimelinePoint[], filterId: string) {
  if (filterId === DEFAULT_FILTER) {
    return points;
  }
  return points.filter((point) => point.filterId === filterId);
}

export function findAlert(alerts: DashboardAlert[], alertId?: string | null) {
  if (!alertId) {
    return null;
  }
  return alerts.find((alert) => alert.id === alertId) ?? null;
}

export function buildHeroSummary(snapshot: DashboardSnapshot, filterId: string) {
  const activeFilter = findFilter(snapshot.filters, filterId);
  if (filterId === 'north-america') {
    return `${activeFilter.teaser} The on-call team is watching retention and repeat purchase softness in the loyalty-heavy segments.`;
  }
  if (filterId === 'europe') {
    return `${activeFilter.teaser} Merch is also tracking late-hydrating price cards, delayed CTA readiness, and a widening gap between high-intent checkout sessions and first-input responsiveness for mobile shoppers crossing price-comparison surfaces.`;
  }
  if (filterId === 'apac') {
    return `${activeFilter.teaser} Growth teams are correlating bounce changes with image-heavy campaign entries and mobile session depth.`;
  }
  return `${activeFilter.teaser} This blended board combines revenue pacing, conversion drift, and live alert ownership across the full regional footprint.`;
}

export function buildLinkedAlertContext(alertOwner: string, filterLabel: string) {
  return `Linked alert context: ${alertOwner} is coordinating the ${filterLabel} mitigation handoff while pricing, retention, and CTA telemetry settle back into the live dashboard after launch.`;
}
