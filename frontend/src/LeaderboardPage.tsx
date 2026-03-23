import { useEffect, useState } from 'react'
import { api } from './api'

interface LeaderboardPageProps {
  tournamentId: number
  tournamentName: string
  onBack: () => void
  onLogout?: () => void
}

export function LeaderboardPage({ tournamentId, tournamentName, onBack, onLogout }: LeaderboardPageProps) {
  const [entries, setEntries] = useState<{ user_id: number; username: string; name: string; points: number }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.leaderboard
      .get(tournamentId)
      .then((r) => setEntries(r.entries))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [tournamentId])

  const btnStyle = {
    padding: '0.25rem 0.5rem' as const,
    fontSize: '0.875rem' as const,
    border: '1px solid #999',
    borderRadius: 4,
    background: 'transparent' as const,
    cursor: 'pointer' as const,
  }
  return (
    <div style={{ maxWidth: 640, margin: '4rem auto', fontFamily: 'system-ui' }}>
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
          <button type="button" onClick={onBack} style={btnStyle}>
            ← Back
          </button>
          {onLogout && (
            <button type="button" onClick={onLogout} style={{ ...btnStyle, marginLeft: 'auto' }}>
              Sign out
            </button>
          )}
        </div>
        <h1 style={{ fontSize: '1.5rem', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>
          Leaderboard — {tournamentName}
        </h1>
      </div>

      {loading && <p style={{ color: '#666' }}>Loading…</p>}
      {error && <p style={{ color: '#c00' }}>{error}</p>}
      {!loading && !error && entries.length === 0 && (
        <p style={{ color: '#666' }}>No scores yet. Scoring logic coming soon.</p>
      )}
      {!loading && !error && entries.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {entries.map((e, i) => (
            <li
              key={e.user_id}
              style={{
                padding: '0.75rem 1rem',
                marginBottom: '0.5rem',
                border: '1px solid #e5e4e7',
                borderRadius: 4,
                background: '#fff',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span>
                {i + 1}. {e.name} (@{e.username})
              </span>
              <strong>{e.points} pts</strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
