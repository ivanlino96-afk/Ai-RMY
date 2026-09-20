import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { LiveViewPage } from './pages/LiveViewPage'
import { PeoplePage } from './pages/PeoplePage'

export function App() {
  return (
    <AppShell>
      {(detection) => (
        <Routes>
          <Route path="/" element={<LiveViewPage detection={detection} />} />
          <Route path="/people" element={<PeoplePage />} />
        </Routes>
      )}
    </AppShell>
  )
}
