import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './views/LoginPage'
import BugListPage from './views/BugListPage'
import BugDetailPage from './views/BugDetailPage'
import BugFormPage from './views/BugFormPage'
import AdminPage from './views/AdminPage'

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
            <BugFormPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/bugs/:id/edit"
        element={
          <ProtectedRoute>
            <BugFormPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/bugs/:id"
        element={
          <ProtectedRoute>
            <BugDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute>
            <AdminPage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/bugs" replace />} />
      <Route path="*" element={<Navigate to="/bugs" replace />} />
    </Routes>
  )
}
