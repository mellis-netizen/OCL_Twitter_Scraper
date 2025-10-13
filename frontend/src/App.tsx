import { useState } from 'react';
import Dashboard from './components/Dashboard';
import AlertDashboard from './components/AlertDashboard';
import CompanyManager from './components/CompanyManager';
import FeedManager from './components/FeedManager';
import ManualControls from './components/ManualControls';
import ErrorBoundary from './components/ErrorBoundary';

type View = 'dashboard' | 'alerts' | 'companies' | 'feeds' | 'controls';

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');

  // Authentication removed - public access enabled

  const navigationItems: { id: View; label: string; icon: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'alerts', label: 'Alerts', icon: '🚨' },
    { id: 'companies', label: 'Companies', icon: '🏢' },
    { id: 'feeds', label: 'Feeds', icon: '📰' },
    { id: 'controls', label: 'Controls', icon: '⚙️' },
  ];

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-dark-950 via-dark-900 to-dark-950">
      {/* Header */}
      <header className="bg-dark-800 border-b border-dark-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <img
                src="https://bafybeihv3qhywegw475lfvrv7qn3fczww6e3y3n5vytkz4qsdw2a3a7xcy.ipfs.dweb.link?filename=0824_Tandem_Primary_Logo_horizontal.jpg"
                alt="Offchain Labs"
                className="h-8 w-auto object-contain rounded"
              />
              <div>
                <h1 className="text-xl font-bold text-white">TGE Monitor</h1>
                <p className="text-xs text-gray-400">Token Generation Event Tracker</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Removed Public Access Mode badge */}
            </div>
          </div>
        </div>
      </header>

      <div className="flex max-w-7xl mx-auto">
        {/* Sidebar Navigation */}
        <aside className="w-64 bg-dark-800 border-r border-dark-700 min-h-screen p-4">
          <nav className="space-y-2">
            {navigationItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left ${
                  currentView === item.id
                    ? 'bg-primary-900 bg-opacity-30 text-primary-300 border border-primary-700'
                    : 'text-gray-400 hover:bg-dark-700 hover:text-gray-200'
                }`}
              >
                <span className="text-xl">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </nav>

          {/* System Status */}
          <div className="mt-8 p-4 bg-dark-700 rounded-lg">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">System Status</h3>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">API</span>
                <span className="flex items-center gap-1 text-green-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                  Online
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Database</span>
                <span className="flex items-center gap-1 text-green-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                  Connected
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">WebSocket</span>
                <span className="flex items-center gap-1 text-green-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                  Live
                </span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {currentView === 'dashboard' && <Dashboard />}
          {currentView === 'alerts' && <AlertDashboard />}
          {currentView === 'companies' && <CompanyManager />}
          {currentView === 'feeds' && <FeedManager />}
          {currentView === 'controls' && <ManualControls />}
        </main>
      </div>

      {/* Footer */}
      <footer className="bg-dark-800 border-t border-dark-700 py-4 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center text-sm text-gray-400">
            <p>
            </p>
            <p className="mt-1 text-xs">
            </p>
          </div>
        </div>
      </footer>
      </div>
    </ErrorBoundary>
  );
}

export default App;
