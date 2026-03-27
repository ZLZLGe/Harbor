import express from 'express';

    const app = express();
    app.use(express.json());

    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    app.get('/api/agent', async (_req, res) => {
      await delay(380);
      res.json({
        id: 'travel-desk-actor-1',
        name: 'Elena Brooks',
        email: 'travel-desk@example.com',
      });
    });

    app.get('/api/offers', async (_req, res) => {
      await delay(520);
      res.json([
        { id: 'travel-desk-1', name: 'Package 1', price: 19.99, category: 'Core', rating: 3, inStock: false },
{ id: 'travel-desk-2', name: 'Package 2', price: 24.34, category: 'Growth', rating: 4, inStock: true },
{ id: 'travel-desk-3', name: 'Package 3', price: 28.69, category: 'Field', rating: 5, inStock: true },
{ id: 'travel-desk-4', name: 'Package 4', price: 33.04, category: 'Specialty', rating: 3, inStock: true },
{ id: 'travel-desk-5', name: 'Package 5', price: 37.39, category: 'Core', rating: 4, inStock: true },
{ id: 'travel-desk-6', name: 'Package 6', price: 41.74, category: 'Growth', rating: 5, inStock: false },
{ id: 'travel-desk-7', name: 'Package 7', price: 46.09, category: 'Field', rating: 3, inStock: true },
{ id: 'travel-desk-8', name: 'Package 8', price: 50.44, category: 'Specialty', rating: 4, inStock: true },
{ id: 'travel-desk-9', name: 'Package 9', price: 54.79, category: 'Core', rating: 5, inStock: true },
{ id: 'travel-desk-10', name: 'Package 10', price: 59.14, category: 'Growth', rating: 3, inStock: true },
{ id: 'travel-desk-11', name: 'Package 11', price: 63.49, category: 'Field', rating: 4, inStock: false },
{ id: 'travel-desk-12', name: 'Package 12', price: 67.84, category: 'Specialty', rating: 5, inStock: true },
{ id: 'travel-desk-13', name: 'Package 13', price: 72.19, category: 'Core', rating: 3, inStock: true },
{ id: 'travel-desk-14', name: 'Package 14', price: 76.54, category: 'Growth', rating: 4, inStock: true },
{ id: 'travel-desk-15', name: 'Package 15', price: 80.89, category: 'Field', rating: 5, inStock: true },
{ id: 'travel-desk-16', name: 'Package 16', price: 85.24, category: 'Specialty', rating: 3, inStock: false },
{ id: 'travel-desk-17', name: 'Package 17', price: 89.59, category: 'Core', rating: 4, inStock: true },
{ id: 'travel-desk-18', name: 'Package 18', price: 93.94, category: 'Growth', rating: 5, inStock: true },
{ id: 'travel-desk-19', name: 'Package 19', price: 98.29, category: 'Field', rating: 3, inStock: true },
{ id: 'travel-desk-20', name: 'Package 20', price: 102.64, category: 'Specialty', rating: 4, inStock: true },
{ id: 'travel-desk-21', name: 'Package 21', price: 106.99, category: 'Core', rating: 5, inStock: false },
{ id: 'travel-desk-22', name: 'Package 22', price: 111.34, category: 'Growth', rating: 3, inStock: true },
{ id: 'travel-desk-23', name: 'Package 23', price: 115.69, category: 'Field', rating: 4, inStock: true },
{ id: 'travel-desk-24', name: 'Package 24', price: 120.04, category: 'Specialty', rating: 5, inStock: true },
{ id: 'travel-desk-25', name: 'Package 25', price: 124.39, category: 'Core', rating: 3, inStock: true },
{ id: 'travel-desk-26', name: 'Package 26', price: 128.74, category: 'Growth', rating: 4, inStock: false },
{ id: 'travel-desk-27', name: 'Package 27', price: 133.09, category: 'Field', rating: 5, inStock: true },
{ id: 'travel-desk-28', name: 'Package 28', price: 137.44, category: 'Specialty', rating: 3, inStock: true },
{ id: 'travel-desk-29', name: 'Package 29', price: 141.79, category: 'Core', rating: 4, inStock: true },
{ id: 'travel-desk-30', name: 'Package 30', price: 146.14, category: 'Growth', rating: 5, inStock: true },
{ id: 'travel-desk-31', name: 'Package 31', price: 150.49, category: 'Field', rating: 3, inStock: false },
{ id: 'travel-desk-32', name: 'Package 32', price: 154.84, category: 'Specialty', rating: 4, inStock: true },
{ id: 'travel-desk-33', name: 'Package 33', price: 159.19, category: 'Core', rating: 5, inStock: true },
{ id: 'travel-desk-34', name: 'Package 34', price: 163.54, category: 'Growth', rating: 3, inStock: true },
{ id: 'travel-desk-35', name: 'Package 35', price: 167.89, category: 'Field', rating: 4, inStock: true },
{ id: 'travel-desk-36', name: 'Package 36', price: 172.24, category: 'Specialty', rating: 5, inStock: false },
{ id: 'travel-desk-37', name: 'Package 37', price: 176.59, category: 'Core', rating: 3, inStock: true },
{ id: 'travel-desk-38', name: 'Package 38', price: 180.94, category: 'Growth', rating: 4, inStock: true },
{ id: 'travel-desk-39', name: 'Package 39', price: 185.29, category: 'Field', rating: 5, inStock: true },
{ id: 'travel-desk-40', name: 'Package 40', price: 189.64, category: 'Specialty', rating: 3, inStock: true },
{ id: 'travel-desk-41', name: 'Package 41', price: 193.99, category: 'Core', rating: 4, inStock: false },
{ id: 'travel-desk-42', name: 'Package 42', price: 198.34, category: 'Growth', rating: 5, inStock: true },
{ id: 'travel-desk-43', name: 'Package 43', price: 202.69, category: 'Field', rating: 3, inStock: true },
{ id: 'travel-desk-44', name: 'Package 44', price: 207.04, category: 'Specialty', rating: 4, inStock: true },
{ id: 'travel-desk-45', name: 'Package 45', price: 211.39, category: 'Core', rating: 5, inStock: true },
{ id: 'travel-desk-46', name: 'Package 46', price: 215.74, category: 'Growth', rating: 3, inStock: false },
{ id: 'travel-desk-47', name: 'Package 47', price: 220.09, category: 'Field', rating: 4, inStock: true },
{ id: 'travel-desk-48', name: 'Package 48', price: 224.44, category: 'Specialty', rating: 5, inStock: true },
{ id: 'travel-desk-49', name: 'Package 49', price: 228.79, category: 'Core', rating: 3, inStock: true },
{ id: 'travel-desk-50', name: 'Package 50', price: 233.14, category: 'Growth', rating: 4, inStock: true },
      ]);
    });

    app.get('/api/reviews', async (_req, res) => {
      await delay(320);
      res.json([
        { id: 'r1', itemId: 'travel-desk-1', text: 'Review 1', rating: 4, author: 'Analyst 1' },
{ id: 'r2', itemId: 'travel-desk-2', text: 'Review 2', rating: 5, author: 'Analyst 2' },
{ id: 'r3', itemId: 'travel-desk-3', text: 'Review 3', rating: 3, author: 'Analyst 3' },
{ id: 'r4', itemId: 'travel-desk-4', text: 'Review 4', rating: 4, author: 'Analyst 4' },
{ id: 'r5', itemId: 'travel-desk-5', text: 'Review 5', rating: 5, author: 'Analyst 5' },
      ]);
    });

    app.get('/api/pricing', async (_req, res) => {
      await delay(620);
      res.json({
        currency: 'USD',
        locale: 'en-US',
        featureFlags: { insights: true },
      });
    });

    app.get('/api/profile/:actorId', async (req, res) => {
      await delay(280);
      res.json({
        actorId: req.params.actorId,
        preferences: { digest: true, theme: 'light' },
      });
    });

    app.post('/api/tracking', async (req, res) => {
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
