import type { Metadata } from 'next';
import { Michroma } from 'next/font/google';
import './(default)/css/globals.css';

const michroma = Michroma({
  weight: '400',
  variable: '--font-michroma',
  subsets: ['latin'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'ASOZ | CV Eşleştirme',
  description: 'AI Destekli Akıllı Özgeçmiş Eşleştirme Platformu',
  applicationName: 'ASOZ | CV Eşleştirme',
  keywords: ['resume', 'matcher', 'job', 'application', 'cv', 'asoz'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-US" className="h-full" suppressHydrationWarning>
      <body
        className={`${michroma.variable} antialiased bg-background text-ink-soft min-h-full font-sans`}
      >
        {children}
      </body>
    </html>
  );
}
