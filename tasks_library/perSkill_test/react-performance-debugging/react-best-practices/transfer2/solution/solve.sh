#!/bin/bash
set -euo pipefail

cd /app

cp /root/oracle/src/app/page.tsx /app/src/app/page.tsx
cp /root/oracle/src/components/CatalogList.tsx /app/src/components/CatalogList.tsx
cp /root/oracle/src/components/CatalogCard.tsx /app/src/components/CatalogCard.tsx
cp /root/oracle/src/components/AdvancedAnalysis.tsx /app/src/components/AdvancedAnalysis.tsx
cp /root/oracle/src/services/api-client.ts /app/src/services/api-client.ts
cp /root/oracle/src/app/api/patients/route.ts /app/src/app/api/patients/route.ts
cp /root/oracle/src/app/api/assignments/route.ts /app/src/app/api/assignments/route.ts
cp /root/oracle/src/app/triage/page.tsx /app/src/app/triage/page.tsx

npm run build
