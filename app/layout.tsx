import './globals.css';
import Sidebar from '@/components/Sidebar';
import GridHelper from '@/components/GridHelper';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'CeaseGuard | C&D Intelligence Dashboard',
  description: 'AI-assisted Cease & Desist classification, risk indexing, and workflow automation.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="page-container">
          <Sidebar />
          <main className="main-content">
            <div className="wrap">
              {children}
              <GridHelper />
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
