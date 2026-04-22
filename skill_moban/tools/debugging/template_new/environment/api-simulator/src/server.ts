import express from 'express';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const app = express();
app.use(express.json());

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const snapshotPath = path.join(__dirname, '../data/analytics_snapshot.json');
const snapshot = JSON.parse(readFileSync(snapshotPath, 'utf-8'));
const snapshotId = snapshot.snapshotId;

app.get('/api/dashboard', async (_req, res) => {
  await delay(240);
  res.setHeader('x-analytics-snapshot', snapshotId);
  res.json(snapshot);
});

app.post('/api/analytics', async (req, res) => {
  await delay(180);
  console.log('dashboard-analytics-event', req.body);
  res.json({ success: true, snapshotId });
});

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', snapshotId, records: snapshot.alerts.length });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Dashboard simulator running on port ${PORT}`);
});
