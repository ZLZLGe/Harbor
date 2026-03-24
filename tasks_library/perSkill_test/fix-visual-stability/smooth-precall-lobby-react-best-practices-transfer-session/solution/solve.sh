#!/bin/bash
set -euo pipefail

cd /app

cat > src/app/layout.tsx <<'EOF'
import type { Metadata } from 'next';
import PreferenceProvider from '@/components/PreferenceProvider';
import './globals.css';

const bootstrapScript = `(function () {
  try {
    var camera = localStorage.getItem('precall-camera-mode');
    var mic = localStorage.getItem('precall-mic-mode');
    var resolvedCamera = camera === 'camera-off' ? 'camera-off' : 'camera-on';
    var resolvedMic = mic === 'mic-muted' ? 'mic-muted' : 'mic-live';
    document.documentElement.setAttribute('data-camera-mode', resolvedCamera);
    document.documentElement.setAttribute('data-mic-mode', resolvedMic);
  } catch (error) {
    document.documentElement.setAttribute('data-camera-mode', 'camera-on');
    document.documentElement.setAttribute('data-mic-mode', 'mic-live');
  }
})();`;

export const metadata: Metadata = {
  title: 'Harbor Meet Precall',
  description: 'Precall lobby before joining the meeting room',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: bootstrapScript }} />
      </head>
      <body>
        <PreferenceProvider>{children}</PreferenceProvider>
      </body>
    </html>
  );
}
EOF

cat > src/app/globals.css <<'EOF'
:root {
  --bg: #f5f7fb;
  --card: #ffffff;
  --card-strong: #14213d;
  --line: #d6dce8;
  --text: #152033;
  --muted: #617089;
  --accent: #2563eb;
  --accent-soft: #dbeafe;
  --danger-soft: #fde7d8;
  --success-soft: #dff5ea;
  --placeholder: #e7ecf5;
  --shadow: 0 18px 50px rgba(19, 31, 56, 0.08);
}

[data-camera-mode='camera-off'] {
  --accent-soft: #e5e7eb;
}

[data-mic-mode='mic-muted'] {
  --success-soft: #fef3c7;
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  min-height: 100%;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 24%),
    linear-gradient(180deg, #f7f9fd 0%, #eef3fb 100%);
  color: var(--text);
  font-family: Arial, sans-serif;
}

body {
  min-height: 100vh;
}

button {
  font: inherit;
}

.app-shell {
  min-height: 100vh;
  padding: 40px 24px 56px;
}

.lobby-shell {
  max-width: 1320px;
  margin: 0 auto;
}

.top-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.top-bar__eyebrow {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.top-bar__title {
  margin: 0;
  font-size: 42px;
  line-height: 1;
}

.top-bar__meta {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 16px;
}

.toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar__button {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--text);
  padding: 12px 18px;
  box-shadow: var(--shadow);
  cursor: pointer;
}

.toolbar__button--primary {
  background: var(--card-strong);
  color: #fff;
  border-color: var(--card-strong);
}

.panel-card {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(214, 220, 232, 0.9);
  border-radius: 28px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(12px);
}

.network-slot {
  min-height: 88px;
  margin-bottom: 20px;
}

.network-banner {
  min-height: 88px;
  display: flex;
  align-items: center;
  padding: 18px 22px;
  border-radius: 24px;
  background: var(--danger-soft);
  border: 1px solid rgba(203, 101, 31, 0.15);
  color: #7a3614;
  box-shadow: var(--shadow);
  transition: opacity 0.2s ease;
}

.network-banner--placeholder {
  opacity: 0.55;
}

.lobby-grid {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.main-column {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.preview-shell {
  padding: 24px;
}

.preview-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 16px;
}

.preview-shell__title {
  margin: 0;
  font-size: 28px;
}

.preview-shell__copy {
  margin: 8px 0 0;
  color: var(--muted);
}

.preview-stage {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  min-height: 420px;
  border-radius: 28px;
  overflow: hidden;
  background: linear-gradient(135deg, #0f172a, #1d4ed8);
}

.preview-stage__canvas {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 30%, rgba(125, 211, 252, 0.35), transparent 24%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(37, 99, 235, 0.88));
}

.preview-stage__canvas--muted {
  background:
    radial-gradient(circle at 30% 30%, rgba(229, 231, 235, 0.22), transparent 24%),
    linear-gradient(135deg, rgba(17, 24, 39, 0.94), rgba(71, 85, 105, 0.88));
}

.preview-stage__overlay {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  color: #fff;
}

.preview-stage__label {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.preview-stage__headline {
  margin: 14px 0 0;
  font-size: 32px;
  max-width: 440px;
}

.preview-stage__subcopy {
  margin: 10px 0 0;
  max-width: 440px;
  line-height: 1.5;
}

.preview-stage__meter {
  width: 180px;
  height: 180px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.14);
  display: grid;
  place-items: center;
}

.preview-stage__meter::after {
  content: '';
  width: 92px;
  height: 92px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.28);
}

.permissions-panel {
  padding: 24px;
}

.section-heading {
  margin: 0 0 16px;
  font-size: 22px;
}

.permissions-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.permission-card {
  padding: 18px;
  border-radius: 22px;
  background: var(--success-soft);
  min-height: 132px;
}

.permission-card--placeholder {
  background: #f8fafc;
}

.permission-card__title {
  margin: 0;
  font-size: 17px;
}

.permission-card__copy {
  margin: 10px 0 0;
  line-height: 1.5;
}

.placeholder-block {
  display: block;
  border-radius: 999px;
  background: var(--placeholder);
}

.permission-card--placeholder .permission-card__title {
  width: 65%;
  height: 18px;
}

.permission-card--placeholder .permission-card__copy {
  width: 100%;
  height: 14px;
  margin-top: 12px;
}

.join-footer {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.join-footer__copy {
  margin: 0;
  color: var(--muted);
}

.join-footer__button {
  border: none;
  border-radius: 999px;
  background: var(--accent);
  color: #fff;
  padding: 14px 22px;
  cursor: pointer;
}

.participants-panel {
  width: 300px;
  flex: 0 0 300px;
  padding: 24px;
}

.participants-panel__meta {
  min-height: 24px;
  margin: 6px 0 0;
  color: var(--muted);
}

.participants-list {
  display: grid;
  gap: 12px;
  min-height: 330px;
  margin-top: 16px;
}

.participant-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 18px;
  background: #f8fafc;
  min-height: 72px;
}

.participant-row--placeholder {
  color: transparent;
}

.participant-row__avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #bfdbfe;
  flex: 0 0 42px;
}

.participant-row__name {
  margin: 0;
  font-weight: 600;
}

.participant-row__role {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 14px;
}

.participant-row--placeholder .participant-row__avatar,
.participant-row--placeholder .participant-row__name,
.participant-row--placeholder .participant-row__role {
  background: var(--placeholder);
}

.participant-row--placeholder .participant-row__name {
  width: 110px;
  height: 14px;
  border-radius: 999px;
}

.participant-row--placeholder .participant-row__role {
  width: 76px;
  height: 12px;
  border-radius: 999px;
  margin-top: 8px;
}

@media (max-width: 1120px) {
  .lobby-grid {
    flex-direction: column;
  }

  .participants-panel {
    width: 100%;
    flex-basis: auto;
  }

  .permissions-grid {
    grid-template-columns: 1fr;
  }
}
EOF

cat > src/components/PreferenceProvider.tsx <<'EOF'
'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import type { CameraMode, MicMode } from '@/data/precallLobby';

const CAMERA_KEY = 'precall-camera-mode';
const MIC_KEY = 'precall-mic-mode';

const PreferenceContext = createContext<{
  cameraMode: CameraMode;
  micMode: MicMode;
  toggleCamera: () => void;
  toggleMic: () => void;
}>({
  cameraMode: 'camera-on',
  micMode: 'mic-live',
  toggleCamera: () => {},
  toggleMic: () => {},
});

function readCameraMode(): CameraMode {
  if (typeof document === 'undefined') {
    return 'camera-on';
  }

  return document.documentElement.getAttribute('data-camera-mode') === 'camera-off'
    ? 'camera-off'
    : 'camera-on';
}

function readMicMode(): MicMode {
  if (typeof document === 'undefined') {
    return 'mic-live';
  }

  return document.documentElement.getAttribute('data-mic-mode') === 'mic-muted'
    ? 'mic-muted'
    : 'mic-live';
}

export function usePreferences() {
  return useContext(PreferenceContext);
}

export default function PreferenceProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [cameraMode, setCameraMode] = useState<CameraMode>(readCameraMode);
  const [micMode, setMicMode] = useState<MicMode>(readMicMode);

  useEffect(() => {
    document.documentElement.setAttribute('data-camera-mode', cameraMode);
    document.documentElement.setAttribute('data-mic-mode', micMode);
    localStorage.setItem(CAMERA_KEY, cameraMode);
    localStorage.setItem(MIC_KEY, micMode);
  }, [cameraMode, micMode]);

  return (
    <PreferenceContext.Provider
      value={{
        cameraMode,
        micMode,
        toggleCamera: () => {
          setCameraMode((current) =>
            current === 'camera-on' ? 'camera-off' : 'camera-on',
          );
        },
        toggleMic: () => {
          setMicMode((current) =>
            current === 'mic-live' ? 'mic-muted' : 'mic-live',
          );
        },
      }}
    >
      <div className="app-shell">{children}</div>
    </PreferenceContext.Provider>
  );
}
EOF

cat > src/components/PrecallLobby.tsx <<'EOF'
'use client';

import { useEffect, useState } from 'react';
import { usePreferences } from '@/components/PreferenceProvider';
import {
  loadNetworkNotice,
  loadParticipants,
  loadPermissions,
  loadPreviewSession,
  type Participant,
  type PermissionCard,
  type PreviewSession,
} from '@/data/precallLobby';

const PARTICIPANT_PLACEHOLDERS = Array.from({ length: 5 }, (_, index) => ({
  id: `placeholder-${index}`,
  name: '',
  role: '',
}));

const PERMISSION_PLACEHOLDERS = Array.from({ length: 3 }, (_, index) => ({
  id: `placeholder-card-${index}`,
  title: '',
  copy: '',
}));

export default function PrecallLobby() {
  const { cameraMode, micMode, toggleCamera, toggleMic } = usePreferences();
  const [notice, setNotice] = useState('');
  const [participants, setParticipants] = useState<Participant[] | null>(null);
  const [permissionCards, setPermissionCards] = useState<PermissionCard[] | null>(null);
  const [preview, setPreview] = useState<PreviewSession | null>(null);

  useEffect(() => {
    let active = true;

    loadNetworkNotice().then((value) => {
      if (active) {
        setNotice(value);
      }
    });

    loadParticipants().then((value) => {
      if (active) {
        setParticipants(value);
      }
    });

    loadPermissions().then((value) => {
      if (active) {
        setPermissionCards(value);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    loadPreviewSession(cameraMode).then((value) => {
      if (active) {
        setPreview(value);
      }
    });

    return () => {
      active = false;
    };
  }, [cameraMode]);

  const visibleParticipants = participants ?? PARTICIPANT_PLACEHOLDERS;
  const visiblePermissionCards = permissionCards ?? PERMISSION_PLACEHOLDERS;

  return (
    <main className="lobby-shell">
      <header className="top-bar">
        <div>
          <p className="top-bar__eyebrow">Harbor meet</p>
          <h1 className="top-bar__title">Design Review Warmup</h1>
          <p className="top-bar__meta">
            11:30 AM HKT · Sydney / Singapore / Seoul room
          </p>
        </div>
        <div className="toolbar">
          <button
            id="camera-toggle"
            data-testid="camera-toggle"
            className="toolbar__button"
            onClick={toggleCamera}
          >
            {cameraMode === 'camera-on' ? 'Turn camera off' : 'Turn camera on'}
          </button>
          <button
            id="mic-toggle"
            data-testid="mic-toggle"
            className="toolbar__button"
            onClick={toggleMic}
          >
            {micMode === 'mic-live' ? 'Mute microphone' : 'Unmute microphone'}
          </button>
          <button className="toolbar__button toolbar__button--primary">
            Join from browser
          </button>
        </div>
      </header>

      <section id="network-slot" data-testid="network-slot" className="network-slot">
        <div
          className={`network-banner ${notice ? '' : 'network-banner--placeholder'}`}
          aria-live="polite"
        >
          {notice || 'Running a quick uplink and packet-loss check for this room.'}
        </div>
      </section>

      <div id="lobby-grid" data-testid="lobby-grid" className="lobby-grid">
        <section id="main-column" data-testid="main-column" className="main-column">
          <section
            id="preview-shell"
            data-testid="preview-shell"
            className="preview-shell panel-card"
          >
            <div className="preview-shell__header">
              <div>
                <h2 className="preview-shell__title">Preview your setup</h2>
                <p className="preview-shell__copy">
                  Check framing, device state and room status before you enter.
                </p>
              </div>
              <span className="toolbar__button">
                {micMode === 'mic-live' ? 'Mic live' : 'Mic muted'}
              </span>
            </div>

            <div id="preview-stage" data-testid="preview-stage" className="preview-stage">
              <div
                className={`preview-stage__canvas ${cameraMode === 'camera-off' ? 'preview-stage__canvas--muted' : ''}`}
              />
              <div className="preview-stage__overlay">
                <div>
                  <span className="preview-stage__label">
                    {preview ? preview.focusLabel : 'Preparing devices'}
                  </span>
                  <h3 className="preview-stage__headline">
                    {preview ? preview.title : 'Connecting your camera preview'}
                  </h3>
                  <p className="preview-stage__subcopy">
                    {preview
                      ? preview.subtitle
                      : 'Reserving the full preview stage before meeting media is ready.'}
                  </p>
                </div>
                <div className="preview-stage__meter" />
              </div>
            </div>
          </section>

          <section
            id="permissions-panel"
            data-testid="permissions-panel"
            className="permissions-panel panel-card"
          >
            <h2 className="section-heading">Permission status</h2>
            <div className="permissions-grid">
              {visiblePermissionCards.map((card) => (
                <article
                  key={card.id}
                  id={`permission-card-${card.id}`}
                  data-testid="permission-card"
                  className={`permission-card ${permissionCards ? '' : 'permission-card--placeholder'}`}
                  aria-hidden={!permissionCards}
                >
                  <h3
                    className={`permission-card__title ${permissionCards ? '' : 'placeholder-block'}`}
                  >
                    {permissionCards ? card.title : ''}
                  </h3>
                  <p
                    className={`permission-card__copy ${permissionCards ? '' : 'placeholder-block'}`}
                  >
                    {permissionCards ? card.copy : ''}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <section
            id="join-footer"
            data-testid="join-footer"
            className="join-footer panel-card"
          >
            <p className="join-footer__copy">
              Meeting locks in 12 minutes. Devices can still be changed after join.
            </p>
            <button className="join-footer__button">Enter lobby</button>
          </section>
        </section>

        <aside
          id="participants-panel"
          data-testid="participants-panel"
          className="participants-panel panel-card"
        >
          <h2 className="section-heading">Already inside</h2>
          <p className="participants-panel__meta">
            {participants
              ? `${participants.length} teammates are active in the room.`
              : 'Reserving seats for people already connected to the room.'}
          </p>
          <div className="participants-list">
            {visibleParticipants.map((participant) => (
              <article
                key={participant.id}
                id={`participant-row-${participant.id}`}
                data-testid="participant-row"
                className={`participant-row ${participants ? '' : 'participant-row--placeholder'}`}
                aria-hidden={!participants}
              >
                <div className="participant-row__avatar" />
                <div>
                  <p className="participant-row__name">
                    {participants ? participant.name : ''}
                  </p>
                  <p className="participant-row__role">
                    {participants ? participant.role : ''}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </aside>
      </div>
    </main>
  );
}
EOF

mkdir -p output
cat > output/precall-lobby-stability-report.json <<'EOF'
{
  "lobby": "precall-readiness",
  "status": "stable",
  "preHydrationBootstrap": {
    "cameraMode": "pre-hydration",
    "micMode": "pre-hydration"
  },
  "checks": [
    {
      "id": "preview-frame-slot",
      "status": "fixed",
      "strategy": "Keep a reserved 16:9 preview stage in the DOM while async meeting media arrives."
    },
    {
      "id": "network-notice-slot",
      "status": "fixed",
      "strategy": "Render a persistent network slot with placeholder copy so the main lobby grid keeps its anchor."
    },
    {
      "id": "participant-rail-slot",
      "status": "fixed",
      "strategy": "Reserve the participant rail width and placeholder rows before attendee data resolves."
    },
    {
      "id": "permission-card-skeleton",
      "status": "fixed",
      "strategy": "Use equal-footprint permission placeholders so the join footer does not move when cards load."
    },
    {
      "id": "device-preference-bootstrap",
      "status": "fixed",
      "strategy": "Apply camera and microphone preferences from localStorage before hydration and initialize React state from those attributes."
    }
  ]
}
EOF
