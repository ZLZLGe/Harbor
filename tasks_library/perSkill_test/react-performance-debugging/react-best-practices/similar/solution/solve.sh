#!/bin/bash
set -euo pipefail

cd /app

cp /root/oracle/src/app/page.tsx /app/src/app/page.tsx
cp /root/oracle/src/components/CatalogList.tsx /app/src/components/CatalogList.tsx
cp /root/oracle/src/components/CatalogCard.tsx /app/src/components/CatalogCard.tsx
cp /root/oracle/src/components/AdvancedAnalysis.tsx /app/src/components/AdvancedAnalysis.tsx
cp /root/oracle/src/services/api-client.ts /app/src/services/api-client.ts
cp /root/oracle/src/app/api/products/route.ts /app/src/app/api/products/route.ts
cp /root/oracle/src/app/api/checkout/route.ts /app/src/app/api/checkout/route.ts
cp /root/oracle/src/app/compare/page.tsx /app/src/app/compare/page.tsx

npm run build
