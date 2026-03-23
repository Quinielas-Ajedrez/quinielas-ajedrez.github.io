import { useEffect, useState } from 'react'
import { api } from './api'

type UserRow = {
  id: number
  name: string
  username: string
  is_admin: boolean
  is_super_admin: boolean
}

interface UsersPageProps {
  onBack: () => void
  onLogout?: () => void
}

export function UsersPage({ onBack, onLogout }: UsersPageProps) {
  const [users, setUsers] = useState<UserRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = () => {
    api.users
      .list()
      .then(setUsers)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    refresh()
  }, [])

  const toggleAdmin = async (u: UserRow) => {
    if (u.is_super_admin) return
    try {
      await api.users.updateAdmin(u.id, !u.is_admin)
      setUsers((prev) =>
        prev.map((x) => (x.id === u.id ? { ...x, is_admin: !x.is_admin } : x))
      )
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update')
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: '4rem auto', fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={onBack}
          style={{
            padding: '0.25rem 0.5rem',
            fontSize: '0.875rem',
            border: '1px solid #999',
            borderRadius: 4,
            background: 'transparent',
            cursor: 'pointer',
          }}
        >
          ← Back
        </button>
        <h1 style={{ fontSize: '1.5rem', margin: 0, flex: 1 }}>Manage users</h1>
        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            style={{
              padding: '0.25rem 0.5rem',
              fontSize: '0.875rem',
              border: '1px solid #999',
              borderRadius: 4,
              background: 'transparent',
              cursor: 'pointer',
            }}
          >
            Sign out
          </button>
        )}
      </div>

      <p style={{ color: '#666', marginBottom: '1rem' }}>
        Toggle admin for users you trust. Super-admins cannot be changed.
      </p>

      {loading && <p style={{ color: '#666' }}>Loading…</p>}
      {error && <p style={{ color: '#c00' }}>{error}</p>}
      {!loading && !error && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {users.map((u) => (
            <li
              key={u.id}
              style={{
                padding: '0.75rem 1rem',
                marginBottom: '0.5rem',
                border: '1px solid #e5e4e7',
                borderRadius: 4,
                background: '#fff',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.5rem',
              }}
            >
              <span>
                <strong>{u.name}</strong> (@{u.username})
                {u.is_super_admin && (
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: '#666' }}>
                    super-admin
                  </span>
                )}
                {u.is_admin && !u.is_super_admin && (
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: '#666' }}>
                    admin
                  </span>
                )}
              </span>
              {!u.is_super_admin && (
                <button
                  type="button"
                  onClick={() => toggleAdmin(u)}
                  style={{
                    padding: '0.25rem 0.5rem',
                    fontSize: '0.875rem',
                    border: '1px solid #999',
                    borderRadius: 4,
                    background: u.is_admin ? '#333' : 'transparent',
                    color: u.is_admin ? '#fff' : '#333',
                    cursor: 'pointer',
                  }}
                >
                  {u.is_admin ? 'Revoke admin' : 'Make admin'}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
