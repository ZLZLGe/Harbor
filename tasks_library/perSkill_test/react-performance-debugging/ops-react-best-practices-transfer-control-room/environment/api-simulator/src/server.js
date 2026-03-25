const express = require('express');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const counters = {
  session: 0,
  incidents: 0,
  serviceHealth: 0,
  deployments: 0,
  approvals: 0,
  policy: 0,
  prepare: 0,
  confirm: 0,
  audit: 0,
};

const seededApprovals = [
  {
    eventId: 'evt-204',
    service: 'Checkout API',
    severity: 'sev-2',
    summary: 'Confirm traffic shed before the regional spike.',
  },
  {
    eventId: 'evt-318',
    service: 'Billing queue',
    severity: 'sev-3',
    summary: 'Approve backlog drain after reconciliation finishes.',
  },
];

function mark(name) {
  counters[name] += 1;
}

function resetCounters() {
  for (const key of Object.keys(counters)) {
    counters[key] = 0;
  }
}

function requireAuth(req, res, next) {
  const authHeader = req.get('authorization') || '';
  if (!authHeader.startsWith('Bearer ctr-')) {
    res.status(401).json({ error: 'missing control room token' });
    return;
  }
  next();
}

app.post('/_diagnostics/reset', (req, res) => {
  resetCounters();
  res.json({ ok: true });
});

app.get('/_diagnostics/stats', (req, res) => {
  res.json({
    counters,
    total: Object.values(counters).reduce((sum, value) => sum + value, 0),
  });
});

app.get('/api/session', async (req, res) => {
  mark('session');
  await delay(320);
  res.json({
    operatorId: 'op-17',
    displayName: 'Mina Chen',
    region: 'apac-south',
    token: 'ctr-live-token',
  });
});

app.get('/api/incidents', requireAuth, async (req, res) => {
  mark('incidents');
  await delay(420);
  res.json([
    {
      incidentId: 'inc-91',
      title: 'SEV-1 Database saturation',
      service: 'Orders DB',
      eta: '12 min',
    },
    {
      incidentId: 'inc-88',
      title: 'SEV-2 Checkout retry storm',
      service: 'Checkout API',
      eta: '18 min',
    },
  ]);
});

app.get('/api/service-health', requireAuth, async (req, res) => {
  mark('serviceHealth');
  await delay(380);
  res.json([
    { service: 'Checkout API', status: 'Degraded', saturation: 87 },
    { service: 'Fulfillment worker', status: 'Healthy', saturation: 58 },
    { service: 'Fraud scoring', status: 'Recovering', saturation: 73 },
  ]);
});

app.get('/api/deployments', requireAuth, async (req, res) => {
  mark('deployments');
  await delay(360);
  res.json([
    { train: 'blue-green-checkout', window: '02:30 UTC', owner: 'release-bot' },
    { train: 'fraud-model-hotfix', window: '03:10 UTC', owner: 'risk-platform' },
  ]);
});

app.get('/api/approvals', requireAuth, async (req, res) => {
  mark('approvals');
  await delay(340);
  res.json(seededApprovals);
});

app.get('/api/policy/:eventId', requireAuth, async (req, res) => {
  mark('policy');
  await delay(260);
  res.json({
    eventId: req.params.eventId,
    runbookId: `runbook-${req.params.eventId}`,
    escalationTarget: 'regional-control-room',
  });
});

app.post('/api/events/:eventId/prepare', requireAuth, async (req, res) => {
  mark('prepare');
  await delay(460);
  const approval = seededApprovals.find((item) => item.eventId === req.params.eventId);
  res.json({
    eventId: req.params.eventId,
    confirmationId: `confirm-${req.params.eventId}`,
    service: approval ? approval.service : 'Unknown service',
  });
});

app.post('/api/events/:eventId/confirm', requireAuth, async (req, res) => {
  mark('confirm');
  await delay(240);
  res.json({
    eventId: req.params.eventId,
    status: 'confirmed',
    confirmationId: req.body.confirmationId,
    runbookId: req.body.runbookId,
  });
});

app.post('/api/audit', async (req, res) => {
  mark('audit');
  await delay(180);
  res.json({ ok: true });
});

app.get('/health', (req, res) => {
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`Control room simulator listening on ${PORT}`);
});
