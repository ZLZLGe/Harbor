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

export default function PrecallLobby() {
  const { cameraMode, micMode, toggleCamera, toggleMic } = usePreferences();
  const [notice, setNotice] = useState('');
  const [participants, setParticipants] = useState<Participant[] | null>(null);
  const [permissionCards, setPermissionCards] = useState<PermissionCard[] | null>(null);
  const [preview, setPreview] = useState<PreviewSession | null>(null);

  useEffect(() => {
    loadNetworkNotice().then(setNotice);
    loadParticipants().then(setParticipants);
    loadPermissions().then(setPermissionCards);
  }, []);

  useEffect(() => {
    setPreview(null);
    loadPreviewSession(cameraMode).then(setPreview);
  }, [cameraMode]);

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

      {notice ? (
        <section id="network-slot" data-testid="network-slot" className="network-slot">
          <div className="network-banner">{notice}</div>
        </section>
      ) : null}

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
            <div
              id="preview-stage"
              data-testid="preview-stage"
              className={`preview-stage ${preview ? 'preview-stage--live' : 'preview-stage--loading'}`}
            >
              <div>
                <span className="preview-stage__label">
                  {preview ? preview.focusLabel : 'Starting devices'}
                </span>
                <h3 className="preview-stage__headline">
                  {preview ? preview.title : 'Connecting your camera preview'}
                </h3>
                <p className="preview-stage__subcopy">
                  {preview
                    ? preview.subtitle
                    : 'Waiting for meeting context, preferred device state and background processing.'}
                </p>
              </div>
              <div className="preview-stage__meter" />
            </div>
          </section>

          <section
            id="permissions-panel"
            data-testid="permissions-panel"
            className="permissions-panel panel-card"
          >
            <h2 className="section-heading">Permission status</h2>
            {permissionCards ? (
              <div className="permissions-grid">
                {permissionCards.map((card) => (
                  <article
                    key={card.id}
                    id={`permission-card-${card.id}`}
                    data-testid="permission-card"
                    className="permission-card"
                  >
                    <h3 className="permission-card__title">{card.title}</h3>
                    <p className="permission-card__copy">{card.copy}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="loading-copy">Checking browser permissions…</p>
            )}
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

        {participants ? (
          <aside
            id="participants-panel"
            data-testid="participants-panel"
            className="participants-panel panel-card"
          >
            <h2 className="section-heading">Already inside</h2>
            <p className="participants-panel__meta">
              {participants.length} teammates are active in the room.
            </p>
            <div className="participants-list">
              {participants.map((participant) => (
                <article
                  key={participant.id}
                  id={`participant-row-${participant.id}`}
                  data-testid="participant-row"
                  className="participant-row"
                >
                  <div className="participant-row__avatar" />
                  <div>
                    <p className="participant-row__name">{participant.name}</p>
                    <p className="participant-row__role">{participant.role}</p>
                  </div>
                </article>
              ))}
            </div>
          </aside>
        ) : null}
      </div>
    </main>
  );
}
