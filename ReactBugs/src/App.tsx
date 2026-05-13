import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './views/LoginPage'
import BugListPage from './views/BugListPage'

function Placeholder({ label }: { label: string }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-gray-500 text-sm">{label} — coming soon</p>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/bugs"
        element={
          <ProtectedRoute>
            <BugListPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/bugs/new"
        element={
          <ProtectedRoute>
            <Placeholder label="New bug" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/bugs/:id/edit"
        element={
          <ProtectedRoute>
            <Placeholder label="Edit bug" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/bugs/:id"
        element={
          <ProtectedRoute>
            <Placeholder label="Bug detail" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute>
            <Placeholder label="Admin" />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/bugs" replace />} />
      <Route path="*" element={<Navigate to="/bugs" replace />} />
    </Routes>
  )
}
