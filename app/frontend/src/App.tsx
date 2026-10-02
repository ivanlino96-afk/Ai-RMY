import { SettingsPage } from './pages/SettingsPage'
import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { LiveViewPage } from './pages/LiveViewPage'
import { ManualModePage } from './pages/ManualModePage'
import { PeoplePage } from './pages/PeoplePage'
import { RoomScanPage } from './pages/RoomScanPage'
import { WelcomePage } from './pages/WelcomePage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route
        path="/*"
        element={
          <AppShell>
            {(detection) => (
              <Routes>
                <Route path="live" element={<LiveViewPage detection={detection} />} />
                <Route path="people" element={<PeoplePage />} />
                <Route path="manual" element={<ManualModePage detection={detection} />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="scan" element={<RoomScanPage detection={detection} />} />
              </Routes>
            )}
          </AppShell>
        }
      />
    </Routes>
  )
}
