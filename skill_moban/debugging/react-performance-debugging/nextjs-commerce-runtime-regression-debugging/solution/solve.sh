#!/bin/bash
set -euo pipefail

cd /app

cp /solution/fixed/src/components/BookCatalog.tsx /app/src/components/BookCatalog.tsx
cp /solution/fixed/src/components/CompareWorkspace.tsx /app/src/components/CompareWorkspace.tsx
cp /solution/fixed/src/components/CompareAdvancedPanel.tsx /app/src/components/CompareAdvancedPanel.tsx
cp /solution/fixed/src/hooks/useShelfProbe.ts /app/src/hooks/useShelfProbe.ts
cp /solution/fixed/src/hooks/useReviewShelfState.ts /app/src/hooks/useReviewShelfState.ts
