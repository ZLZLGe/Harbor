import express from 'express';

    const app = express();
    app.use(express.json());

    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    app.get('/api/user', async (_req, res) => {
      await delay(380);
      res.json({
        id: 'storefront-actor-1',
        name: 'Morgan Lee',
        email: 'storefront@example.com',
      });
    });

    app.get('/api/products', async (_req, res) => {
      await delay(520);
      res.json([
        { id: 'storefront-1', name: 'Product 1', price: 19.99, category: 'Core', rating: 3, inStock: false },
{ id: 'storefront-2', name: 'Product 2', price: 24.34, category: 'Growth', rating: 4, inStock: true },
{ id: 'storefront-3', name: 'Product 3', price: 28.69, category: 'Field', rating: 5, inStock: true },
{ id: 'storefront-4', name: 'Product 4', price: 33.04, category: 'Specialty', rating: 3, inStock: true },
{ id: 'storefront-5', name: 'Product 5', price: 37.39, category: 'Core', rating: 4, inStock: true },
{ id: 'storefront-6', name: 'Product 6', price: 41.74, category: 'Growth', rating: 5, inStock: false },
{ id: 'storefront-7', name: 'Product 7', price: 46.09, category: 'Field', rating: 3, inStock: true },
{ id: 'storefront-8', name: 'Product 8', price: 50.44, category: 'Specialty', rating: 4, inStock: true },
{ id: 'storefront-9', name: 'Product 9', price: 54.79, category: 'Core', rating: 5, inStock: true },
{ id: 'storefront-10', name: 'Product 10', price: 59.14, category: 'Growth', rating: 3, inStock: true },
{ id: 'storefront-11', name: 'Product 11', price: 63.49, category: 'Field', rating: 4, inStock: false },
{ id: 'storefront-12', name: 'Product 12', price: 67.84, category: 'Specialty', rating: 5, inStock: true },
{ id: 'storefront-13', name: 'Product 13', price: 72.19, category: 'Core', rating: 3, inStock: true },
{ id: 'storefront-14', name: 'Product 14', price: 76.54, category: 'Growth', rating: 4, inStock: true },
{ id: 'storefront-15', name: 'Product 15', price: 80.89, category: 'Field', rating: 5, inStock: true },
{ id: 'storefront-16', name: 'Product 16', price: 85.24, category: 'Specialty', rating: 3, inStock: false },
{ id: 'storefront-17', name: 'Product 17', price: 89.59, category: 'Core', rating: 4, inStock: true },
{ id: 'storefront-18', name: 'Product 18', price: 93.94, category: 'Growth', rating: 5, inStock: true },
{ id: 'storefront-19', name: 'Product 19', price: 98.29, category: 'Field', rating: 3, inStock: true },
{ id: 'storefront-20', name: 'Product 20', price: 102.64, category: 'Specialty', rating: 4, inStock: true },
{ id: 'storefront-21', name: 'Product 21', price: 106.99, category: 'Core', rating: 5, inStock: false },
{ id: 'storefront-22', name: 'Product 22', price: 111.34, category: 'Growth', rating: 3, inStock: true },
{ id: 'storefront-23', name: 'Product 23', price: 115.69, category: 'Field', rating: 4, inStock: true },
{ id: 'storefront-24', name: 'Product 24', price: 120.04, category: 'Specialty', rating: 5, inStock: true },
{ id: 'storefront-25', name: 'Product 25', price: 124.39, category: 'Core', rating: 3, inStock: true },
{ id: 'storefront-26', name: 'Product 26', price: 128.74, category: 'Growth', rating: 4, inStock: false },
{ id: 'storefront-27', name: 'Product 27', price: 133.09, category: 'Field', rating: 5, inStock: true },
{ id: 'storefront-28', name: 'Product 28', price: 137.44, category: 'Specialty', rating: 3, inStock: true },
{ id: 'storefront-29', name: 'Product 29', price: 141.79, category: 'Core', rating: 4, inStock: true },
{ id: 'storefront-30', name: 'Product 30', price: 146.14, category: 'Growth', rating: 5, inStock: true },
{ id: 'storefront-31', name: 'Product 31', price: 150.49, category: 'Field', rating: 3, inStock: false },
{ id: 'storefront-32', name: 'Product 32', price: 154.84, category: 'Specialty', rating: 4, inStock: true },
{ id: 'storefront-33', name: 'Product 33', price: 159.19, category: 'Core', rating: 5, inStock: true },
{ id: 'storefront-34', name: 'Product 34', price: 163.54, category: 'Growth', rating: 3, inStock: true },
{ id: 'storefront-35', name: 'Product 35', price: 167.89, category: 'Field', rating: 4, inStock: true },
{ id: 'storefront-36', name: 'Product 36', price: 172.24, category: 'Specialty', rating: 5, inStock: false },
{ id: 'storefront-37', name: 'Product 37', price: 176.59, category: 'Core', rating: 3, inStock: true },
{ id: 'storefront-38', name: 'Product 38', price: 180.94, category: 'Growth', rating: 4, inStock: true },
{ id: 'storefront-39', name: 'Product 39', price: 185.29, category: 'Field', rating: 5, inStock: true },
{ id: 'storefront-40', name: 'Product 40', price: 189.64, category: 'Specialty', rating: 3, inStock: true },
{ id: 'storefront-41', name: 'Product 41', price: 193.99, category: 'Core', rating: 4, inStock: false },
{ id: 'storefront-42', name: 'Product 42', price: 198.34, category: 'Growth', rating: 5, inStock: true },
{ id: 'storefront-43', name: 'Product 43', price: 202.69, category: 'Field', rating: 3, inStock: true },
{ id: 'storefront-44', name: 'Product 44', price: 207.04, category: 'Specialty', rating: 4, inStock: true },
{ id: 'storefront-45', name: 'Product 45', price: 211.39, category: 'Core', rating: 5, inStock: true },
{ id: 'storefront-46', name: 'Product 46', price: 215.74, category: 'Growth', rating: 3, inStock: false },
{ id: 'storefront-47', name: 'Product 47', price: 220.09, category: 'Field', rating: 4, inStock: true },
{ id: 'storefront-48', name: 'Product 48', price: 224.44, category: 'Specialty', rating: 5, inStock: true },
{ id: 'storefront-49', name: 'Product 49', price: 228.79, category: 'Core', rating: 3, inStock: true },
{ id: 'storefront-50', name: 'Product 50', price: 233.14, category: 'Growth', rating: 4, inStock: true },
      ]);
    });

    app.get('/api/reviews', async (_req, res) => {
      await delay(320);
      res.json([
        { id: 'r1', itemId: 'storefront-1', text: 'Review 1', rating: 4, author: 'Analyst 1' },
{ id: 'r2', itemId: 'storefront-2', text: 'Review 2', rating: 5, author: 'Analyst 2' },
{ id: 'r3', itemId: 'storefront-3', text: 'Review 3', rating: 3, author: 'Analyst 3' },
{ id: 'r4', itemId: 'storefront-4', text: 'Review 4', rating: 4, author: 'Analyst 4' },
{ id: 'r5', itemId: 'storefront-5', text: 'Review 5', rating: 5, author: 'Analyst 5' },
      ]);
    });

    app.get('/api/config', async (_req, res) => {
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

    app.post('/api/analytics', async (req, res) => {
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
