import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { LiveViewPage } from './pages/LiveViewPage'
import { ManualModePage } from './pages/ManualModePage'
import { PeoplePage } from './pages/PeoplePage'
import { RoomScanPage } from './pages/RoomScanPage'

export function App() {
  return (
    <AppShell>
      {(detection) => (
        <Routes>
          <Route path="/" element={<LiveViewPage detection={detection} />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/manual" element={<ManualModePage detection={detection} />} />
          <Route path="/scan" element={<RoomScanPage detection={detection} />} />
        </Routes>
      )}
    </AppShell>
  )
}
