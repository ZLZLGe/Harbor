import express from 'express';

    const app = express();
    app.use(express.json());

    const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    app.get('/api/coach', async (_req, res) => {
      await delay(380);
      res.json({
        id: 'course-planner-actor-1',
        name: 'Dana Ortiz',
        email: 'course-planner@example.com',
      });
    });

    app.get('/api/courses', async (_req, res) => {
      await delay(520);
      res.json([
        { id: 'course-planner-1', name: 'Course 1', price: 19.99, category: 'Core', rating: 3, inStock: false },
{ id: 'course-planner-2', name: 'Course 2', price: 24.34, category: 'Growth', rating: 4, inStock: true },
{ id: 'course-planner-3', name: 'Course 3', price: 28.69, category: 'Field', rating: 5, inStock: true },
{ id: 'course-planner-4', name: 'Course 4', price: 33.04, category: 'Specialty', rating: 3, inStock: true },
{ id: 'course-planner-5', name: 'Course 5', price: 37.39, category: 'Core', rating: 4, inStock: true },
{ id: 'course-planner-6', name: 'Course 6', price: 41.74, category: 'Growth', rating: 5, inStock: false },
{ id: 'course-planner-7', name: 'Course 7', price: 46.09, category: 'Field', rating: 3, inStock: true },
{ id: 'course-planner-8', name: 'Course 8', price: 50.44, category: 'Specialty', rating: 4, inStock: true },
{ id: 'course-planner-9', name: 'Course 9', price: 54.79, category: 'Core', rating: 5, inStock: true },
{ id: 'course-planner-10', name: 'Course 10', price: 59.14, category: 'Growth', rating: 3, inStock: true },
{ id: 'course-planner-11', name: 'Course 11', price: 63.49, category: 'Field', rating: 4, inStock: false },
{ id: 'course-planner-12', name: 'Course 12', price: 67.84, category: 'Specialty', rating: 5, inStock: true },
{ id: 'course-planner-13', name: 'Course 13', price: 72.19, category: 'Core', rating: 3, inStock: true },
{ id: 'course-planner-14', name: 'Course 14', price: 76.54, category: 'Growth', rating: 4, inStock: true },
{ id: 'course-planner-15', name: 'Course 15', price: 80.89, category: 'Field', rating: 5, inStock: true },
{ id: 'course-planner-16', name: 'Course 16', price: 85.24, category: 'Specialty', rating: 3, inStock: false },
{ id: 'course-planner-17', name: 'Course 17', price: 89.59, category: 'Core', rating: 4, inStock: true },
{ id: 'course-planner-18', name: 'Course 18', price: 93.94, category: 'Growth', rating: 5, inStock: true },
{ id: 'course-planner-19', name: 'Course 19', price: 98.29, category: 'Field', rating: 3, inStock: true },
{ id: 'course-planner-20', name: 'Course 20', price: 102.64, category: 'Specialty', rating: 4, inStock: true },
{ id: 'course-planner-21', name: 'Course 21', price: 106.99, category: 'Core', rating: 5, inStock: false },
{ id: 'course-planner-22', name: 'Course 22', price: 111.34, category: 'Growth', rating: 3, inStock: true },
{ id: 'course-planner-23', name: 'Course 23', price: 115.69, category: 'Field', rating: 4, inStock: true },
{ id: 'course-planner-24', name: 'Course 24', price: 120.04, category: 'Specialty', rating: 5, inStock: true },
{ id: 'course-planner-25', name: 'Course 25', price: 124.39, category: 'Core', rating: 3, inStock: true },
{ id: 'course-planner-26', name: 'Course 26', price: 128.74, category: 'Growth', rating: 4, inStock: false },
{ id: 'course-planner-27', name: 'Course 27', price: 133.09, category: 'Field', rating: 5, inStock: true },
{ id: 'course-planner-28', name: 'Course 28', price: 137.44, category: 'Specialty', rating: 3, inStock: true },
{ id: 'course-planner-29', name: 'Course 29', price: 141.79, category: 'Core', rating: 4, inStock: true },
{ id: 'course-planner-30', name: 'Course 30', price: 146.14, category: 'Growth', rating: 5, inStock: true },
{ id: 'course-planner-31', name: 'Course 31', price: 150.49, category: 'Field', rating: 3, inStock: false },
{ id: 'course-planner-32', name: 'Course 32', price: 154.84, category: 'Specialty', rating: 4, inStock: true },
{ id: 'course-planner-33', name: 'Course 33', price: 159.19, category: 'Core', rating: 5, inStock: true },
{ id: 'course-planner-34', name: 'Course 34', price: 163.54, category: 'Growth', rating: 3, inStock: true },
{ id: 'course-planner-35', name: 'Course 35', price: 167.89, category: 'Field', rating: 4, inStock: true },
{ id: 'course-planner-36', name: 'Course 36', price: 172.24, category: 'Specialty', rating: 5, inStock: false },
{ id: 'course-planner-37', name: 'Course 37', price: 176.59, category: 'Core', rating: 3, inStock: true },
{ id: 'course-planner-38', name: 'Course 38', price: 180.94, category: 'Growth', rating: 4, inStock: true },
{ id: 'course-planner-39', name: 'Course 39', price: 185.29, category: 'Field', rating: 5, inStock: true },
{ id: 'course-planner-40', name: 'Course 40', price: 189.64, category: 'Specialty', rating: 3, inStock: true },
{ id: 'course-planner-41', name: 'Course 41', price: 193.99, category: 'Core', rating: 4, inStock: false },
{ id: 'course-planner-42', name: 'Course 42', price: 198.34, category: 'Growth', rating: 5, inStock: true },
{ id: 'course-planner-43', name: 'Course 43', price: 202.69, category: 'Field', rating: 3, inStock: true },
{ id: 'course-planner-44', name: 'Course 44', price: 207.04, category: 'Specialty', rating: 4, inStock: true },
{ id: 'course-planner-45', name: 'Course 45', price: 211.39, category: 'Core', rating: 5, inStock: true },
{ id: 'course-planner-46', name: 'Course 46', price: 215.74, category: 'Growth', rating: 3, inStock: false },
{ id: 'course-planner-47', name: 'Course 47', price: 220.09, category: 'Field', rating: 4, inStock: true },
{ id: 'course-planner-48', name: 'Course 48', price: 224.44, category: 'Specialty', rating: 5, inStock: true },
{ id: 'course-planner-49', name: 'Course 49', price: 228.79, category: 'Core', rating: 3, inStock: true },
{ id: 'course-planner-50', name: 'Course 50', price: 233.14, category: 'Growth', rating: 4, inStock: true },
      ]);
    });

    app.get('/api/feedback', async (_req, res) => {
      await delay(320);
      res.json([
        { id: 'r1', itemId: 'course-planner-1', text: 'Review 1', rating: 4, author: 'Analyst 1' },
{ id: 'r2', itemId: 'course-planner-2', text: 'Review 2', rating: 5, author: 'Analyst 2' },
{ id: 'r3', itemId: 'course-planner-3', text: 'Review 3', rating: 3, author: 'Analyst 3' },
{ id: 'r4', itemId: 'course-planner-4', text: 'Review 4', rating: 4, author: 'Analyst 4' },
{ id: 'r5', itemId: 'course-planner-5', text: 'Review 5', rating: 5, author: 'Analyst 5' },
      ]);
    });

    app.get('/api/preferences', async (_req, res) => {
      await delay(620);
      res.json({
        currency: 'USD',
        locale: 'en-US',
        featureFlags: { insights: true },
      });
    });

    app.get('/api/progress/:actorId', async (req, res) => {
      await delay(280);
      res.json({
        actorId: req.params.actorId,
        preferences: { digest: true, theme: 'light' },
      });
    });

    app.post('/api/events', async (req, res) => {
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
