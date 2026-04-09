#!/bin/bash
set -euo pipefail

cd /app

cp /solution/fixed/src/components/DashboardShell.tsx /app/src/components/DashboardShell.tsx
cp /solution/fixed/src/components/TimelinePanel.tsx /app/src/components/TimelinePanel.tsx
cp /solution/fixed/src/hooks/useDashboardProbe.ts /app/src/hooks/useDashboardProbe.ts
cp /solution/fixed/src/hooks/useDashboardFilterState.ts /app/src/hooks/useDashboardFilterState.ts
cp /solution/fixed/src/lib/dashboardRefreshTelemetry.ts /app/src/lib/dashboardRefreshTelemetry.ts
