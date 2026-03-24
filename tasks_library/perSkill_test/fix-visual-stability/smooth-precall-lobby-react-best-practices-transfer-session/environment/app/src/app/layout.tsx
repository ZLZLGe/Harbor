import type { Metadata } from 'next';
import PreferenceProvider from '@/components/PreferenceProvider';
import './globals.css';

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
    <html lang="en">
      <body>
        <PreferenceProvider>{children}</PreferenceProvider>
      </body>
    </html>
  );
}
