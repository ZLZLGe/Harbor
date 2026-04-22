import express from 'express';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const app = express();
app.use(express.json());

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const snapshotPath = path.join(__dirname, '../data/books_snapshot.json');
const books = JSON.parse(readFileSync(snapshotPath, 'utf-8'));
const snapshotId = 'gutendex-fiction-en-2026-04-06';

app.get('/api/books', async (_req, res) => {
  await delay(220);
  res.setHeader('x-catalog-snapshot', snapshotId);
  res.json(books);
});

app.post('/api/analytics', async (req, res) => {
  await delay(180);
  console.log('catalog-analytics-event', req.body);
  res.json({ success: true, snapshotId });
});

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', snapshotId, records: books.length });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Catalog simulator running on port ${PORT}`);
});
