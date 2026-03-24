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

export function usePreferences() {
  return useContext(PreferenceContext);
}

export default function PreferenceProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [cameraMode, setCameraMode] = useState<CameraMode>('camera-on');
  const [micMode, setMicMode] = useState<MicMode>('mic-live');

  useEffect(() => {
    const storedCamera = localStorage.getItem(CAMERA_KEY);
    const storedMic = localStorage.getItem(MIC_KEY);

    if (storedCamera === 'camera-off') {
      setCameraMode('camera-off');
    }

    if (storedMic === 'mic-muted') {
      setMicMode('mic-muted');
    }
  }, []);

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
