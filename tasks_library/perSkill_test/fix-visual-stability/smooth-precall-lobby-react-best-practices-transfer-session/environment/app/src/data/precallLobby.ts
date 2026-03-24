export type CameraMode = 'camera-on' | 'camera-off';
export type MicMode = 'mic-live' | 'mic-muted';

export interface PreviewSession {
  title: string;
  subtitle: string;
  focusLabel: string;
}

export interface Participant {
  id: string;
  name: string;
  role: string;
}

export interface PermissionCard {
  id: string;
  title: string;
  copy: string;
}

const participants: Participant[] = [
  { id: 'parker', name: 'Parker Reed', role: 'Host' },
  { id: 'maya', name: 'Maya Lin', role: 'Product Design' },
  { id: 'noah', name: 'Noah Fields', role: 'Frontend' },
  { id: 'sana', name: 'Sana Ali', role: 'Research' },
  { id: 'jules', name: 'Jules Hart', role: 'Customer Success' },
];

const permissionCards: PermissionCard[] = [
  {
    id: 'camera',
    title: 'Camera permission',
    copy: 'The browser can access your camera when you join the room.',
  },
  {
    id: 'microphone',
    title: 'Microphone permission',
    copy: 'Your selected microphone is ready for echo cancellation.',
  },
  {
    id: 'speaker',
    title: 'Speaker output',
    copy: 'System audio is routed to your default headset device.',
  },
];

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function loadNetworkNotice() {
  await delay(1400);
  return 'Network check complete. Your current uplink can support HD video for this meeting.';
}

export async function loadPreviewSession(cameraMode: CameraMode): Promise<PreviewSession> {
  await delay(900);

  if (cameraMode === 'camera-off') {
    return {
      title: 'Camera is paused before join',
      subtitle: 'You are still reserving bandwidth and device settings for the live room.',
      focusLabel: 'Camera off',
    };
  }

  return {
    title: 'You are framed and ready for the room',
    subtitle: 'Face positioning, background blur and meeting lighting are all applied.',
    focusLabel: 'Camera on',
  };
}

export async function loadParticipants() {
  await delay(1700);
  return participants;
}

export async function loadPermissions() {
  await delay(1100);
  return permissionCards;
}
