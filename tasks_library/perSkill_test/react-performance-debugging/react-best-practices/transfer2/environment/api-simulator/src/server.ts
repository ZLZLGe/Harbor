import express from 'express';

    const app = express();
    app.use(express.json());

    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    app.get('/api/dispatcher', async (_req, res) => {
      await delay(380);
      res.json({
        id: 'triage-board-actor-1',
        name: 'Priya Shah',
        email: 'triage-board@example.com',
      });
    });

    app.get('/api/patients', async (_req, res) => {
      await delay(520);
      res.json([
        { id: 'triage-board-1', name: 'Patient 1', price: 19.99, category: 'Core', rating: 3, inStock: false },
{ id: 'triage-board-2', name: 'Patient 2', price: 24.34, category: 'Growth', rating: 4, inStock: true },
{ id: 'triage-board-3', name: 'Patient 3', price: 28.69, category: 'Field', rating: 5, inStock: true },
{ id: 'triage-board-4', name: 'Patient 4', price: 33.04, category: 'Specialty', rating: 3, inStock: true },
{ id: 'triage-board-5', name: 'Patient 5', price: 37.39, category: 'Core', rating: 4, inStock: true },
{ id: 'triage-board-6', name: 'Patient 6', price: 41.74, category: 'Growth', rating: 5, inStock: false },
{ id: 'triage-board-7', name: 'Patient 7', price: 46.09, category: 'Field', rating: 3, inStock: true },
{ id: 'triage-board-8', name: 'Patient 8', price: 50.44, category: 'Specialty', rating: 4, inStock: true },
{ id: 'triage-board-9', name: 'Patient 9', price: 54.79, category: 'Core', rating: 5, inStock: true },
{ id: 'triage-board-10', name: 'Patient 10', price: 59.14, category: 'Growth', rating: 3, inStock: true },
{ id: 'triage-board-11', name: 'Patient 11', price: 63.49, category: 'Field', rating: 4, inStock: false },
{ id: 'triage-board-12', name: 'Patient 12', price: 67.84, category: 'Specialty', rating: 5, inStock: true },
{ id: 'triage-board-13', name: 'Patient 13', price: 72.19, category: 'Core', rating: 3, inStock: true },
{ id: 'triage-board-14', name: 'Patient 14', price: 76.54, category: 'Growth', rating: 4, inStock: true },
{ id: 'triage-board-15', name: 'Patient 15', price: 80.89, category: 'Field', rating: 5, inStock: true },
{ id: 'triage-board-16', name: 'Patient 16', price: 85.24, category: 'Specialty', rating: 3, inStock: false },
{ id: 'triage-board-17', name: 'Patient 17', price: 89.59, category: 'Core', rating: 4, inStock: true },
{ id: 'triage-board-18', name: 'Patient 18', price: 93.94, category: 'Growth', rating: 5, inStock: true },
{ id: 'triage-board-19', name: 'Patient 19', price: 98.29, category: 'Field', rating: 3, inStock: true },
{ id: 'triage-board-20', name: 'Patient 20', price: 102.64, category: 'Specialty', rating: 4, inStock: true },
{ id: 'triage-board-21', name: 'Patient 21', price: 106.99, category: 'Core', rating: 5, inStock: false },
{ id: 'triage-board-22', name: 'Patient 22', price: 111.34, category: 'Growth', rating: 3, inStock: true },
{ id: 'triage-board-23', name: 'Patient 23', price: 115.69, category: 'Field', rating: 4, inStock: true },
{ id: 'triage-board-24', name: 'Patient 24', price: 120.04, category: 'Specialty', rating: 5, inStock: true },
{ id: 'triage-board-25', name: 'Patient 25', price: 124.39, category: 'Core', rating: 3, inStock: true },
{ id: 'triage-board-26', name: 'Patient 26', price: 128.74, category: 'Growth', rating: 4, inStock: false },
{ id: 'triage-board-27', name: 'Patient 27', price: 133.09, category: 'Field', rating: 5, inStock: true },
{ id: 'triage-board-28', name: 'Patient 28', price: 137.44, category: 'Specialty', rating: 3, inStock: true },
{ id: 'triage-board-29', name: 'Patient 29', price: 141.79, category: 'Core', rating: 4, inStock: true },
{ id: 'triage-board-30', name: 'Patient 30', price: 146.14, category: 'Growth', rating: 5, inStock: true },
{ id: 'triage-board-31', name: 'Patient 31', price: 150.49, category: 'Field', rating: 3, inStock: false },
{ id: 'triage-board-32', name: 'Patient 32', price: 154.84, category: 'Specialty', rating: 4, inStock: true },
{ id: 'triage-board-33', name: 'Patient 33', price: 159.19, category: 'Core', rating: 5, inStock: true },
{ id: 'triage-board-34', name: 'Patient 34', price: 163.54, category: 'Growth', rating: 3, inStock: true },
{ id: 'triage-board-35', name: 'Patient 35', price: 167.89, category: 'Field', rating: 4, inStock: true },
{ id: 'triage-board-36', name: 'Patient 36', price: 172.24, category: 'Specialty', rating: 5, inStock: false },
{ id: 'triage-board-37', name: 'Patient 37', price: 176.59, category: 'Core', rating: 3, inStock: true },
{ id: 'triage-board-38', name: 'Patient 38', price: 180.94, category: 'Growth', rating: 4, inStock: true },
{ id: 'triage-board-39', name: 'Patient 39', price: 185.29, category: 'Field', rating: 5, inStock: true },
{ id: 'triage-board-40', name: 'Patient 40', price: 189.64, category: 'Specialty', rating: 3, inStock: true },
{ id: 'triage-board-41', name: 'Patient 41', price: 193.99, category: 'Core', rating: 4, inStock: false },
{ id: 'triage-board-42', name: 'Patient 42', price: 198.34, category: 'Growth', rating: 5, inStock: true },
{ id: 'triage-board-43', name: 'Patient 43', price: 202.69, category: 'Field', rating: 3, inStock: true },
{ id: 'triage-board-44', name: 'Patient 44', price: 207.04, category: 'Specialty', rating: 4, inStock: true },
{ id: 'triage-board-45', name: 'Patient 45', price: 211.39, category: 'Core', rating: 5, inStock: true },
{ id: 'triage-board-46', name: 'Patient 46', price: 215.74, category: 'Growth', rating: 3, inStock: false },
{ id: 'triage-board-47', name: 'Patient 47', price: 220.09, category: 'Field', rating: 4, inStock: true },
{ id: 'triage-board-48', name: 'Patient 48', price: 224.44, category: 'Specialty', rating: 5, inStock: true },
{ id: 'triage-board-49', name: 'Patient 49', price: 228.79, category: 'Core', rating: 3, inStock: true },
{ id: 'triage-board-50', name: 'Patient 50', price: 233.14, category: 'Growth', rating: 4, inStock: true },
      ]);
    });

    app.get('/api/notes', async (_req, res) => {
      await delay(320);
      res.json([
        { id: 'r1', itemId: 'triage-board-1', text: 'Review 1', rating: 4, author: 'Analyst 1' },
{ id: 'r2', itemId: 'triage-board-2', text: 'Review 2', rating: 5, author: 'Analyst 2' },
{ id: 'r3', itemId: 'triage-board-3', text: 'Review 3', rating: 3, author: 'Analyst 3' },
{ id: 'r4', itemId: 'triage-board-4', text: 'Review 4', rating: 4, author: 'Analyst 4' },
{ id: 'r5', itemId: 'triage-board-5', text: 'Review 5', rating: 5, author: 'Analyst 5' },
      ]);
    });

    app.get('/api/policy', async (_req, res) => {
      await delay(620);
      res.json({
        currency: 'USD',
        locale: 'en-US',
        featureFlags: { insights: true },
      });
    });

    app.get('/api/roster/:actorId', async (req, res) => {
      await delay(280);
      res.json({
        actorId: req.params.actorId,
        preferences: { digest: true, theme: 'light' },
      });
    });

    app.post('/api/telemetry', async (req, res) => {
      await delay(180);
      console.log('Logged event:', req.body);
      res.json({ success: true });
    });

    app.get('/health', (_req, res) => {
      res.json({ status: 'ok' });
    });

    const PORT = process.env.PORT || 3001;
    app.listen(PORT, () => {
      console.log(`API Simulator running on port ${PORT}`);
    });
