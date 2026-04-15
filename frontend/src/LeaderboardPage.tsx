import { useEffect, useState } from 'react'
import { api } from './api'

interface LeaderboardPageProps {
  tournamentId: number
  tournamentName: string
  onBack: () => void
  onLogout?: () => void
}

type LeaderboardEntry = {
  user_id: number
  username: string
  name: string
  points: number
  points_rounds: number
  points_table: number
}

export function LeaderboardPage({ tournamentId, tournamentName, onBack, onLogout }: LeaderboardPageProps) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
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

  const thTd = {
    padding: '0.5rem 0.65rem' as const,
    textAlign: 'left' as const,
    fontSize: '0.875rem' as const,
  }

  const numCell = { ...thTd, textAlign: 'right' as const, fontVariantNumeric: 'tabular-nums' as const }

  return (
    <div style={{ maxWidth: 720, margin: '4rem auto', fontFamily: 'system-ui' }}>
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
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              border: '1px solid #e5e4e7',
              borderRadius: 4,
              background: '#fff',
            }}
          >
            <thead>
              <tr style={{ background: '#fafafa', borderBottom: '1px solid #e5e4e7' }}>
                <th style={thTd}>#</th>
                <th style={thTd}>Player</th>
                <th style={numCell} title="Points from per-round game predictions">
                  Rounds
                </th>
                <th style={numCell} title="Points from final table prediction">
                  Table
                </th>
                <th style={numCell} title="Rounds + table">
                  Total
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={e.user_id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={thTd}>{i + 1}</td>
                  <td style={thTd}>
                    {e.name} <span style={{ color: '#777' }}>(@{e.username})</span>
                  </td>
                  <td style={numCell}>{e.points_rounds}</td>
                  <td style={numCell}>{e.points_table}</td>
                  <td style={{ ...numCell, fontWeight: 600 }}>{e.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
