/**
 * Super-admin view: how many users picked each result per board.
 *
 * Future: replace or supplement the table with plots (bar/stacked charts per game,
 * distribution across rounds, etc.) once a chart library is chosen.
 */

import { useEffect, useState } from 'react'
import { api } from './api'

interface StatisticsPageProps {
  tournamentId: number
  tournamentName: string
  onBack: () => void
  onLogout?: () => void
}

const btnStyle = {
  padding: '0.25rem 0.5rem' as const,
  fontSize: '0.875rem' as const,
  border: '1px solid #999',
  borderRadius: 4,
  background: 'transparent' as const,
  cursor: 'pointer' as const,
}

export function StatisticsPage({
  tournamentId,
  tournamentName,
  onBack,
  onLogout,
}: StatisticsPageProps) {
  const [data, setData] = useState<
    | {
        games: {
          game_id: number
          white_player: string
          black_player: string
          round_name: string
          counts: Record<string, number>
        }[]
      }
    | null
  >(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api.tournaments
      .predictionStatistics(tournamentId)
      .then((d) => {
        if (!cancelled) {
          setData(d)
          setErr('')
        }
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Failed to load')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [tournamentId])

  return (
    <div style={{ maxWidth: 640, margin: '4rem auto', fontFamily: 'system-ui' }}>
      <div style={{ marginBottom: '1rem' }}>
        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
            flexWrap: 'wrap',
            marginBottom: '0.5rem',
          }}
        >
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
          Statistics — {tournamentName}
        </h1>
        <p style={{ fontSize: '0.8125rem', color: '#666', marginTop: '0.35rem', marginBottom: 0 }}>
          Super-admin: prediction counts per game (how many users chose each result).
        </p>
      </div>

      {loading && <p style={{ color: '#666' }}>Loading…</p>}
      {err && <p style={{ color: '#c00' }}>{err}</p>}
      {data && !loading && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>
                <th style={{ padding: '0.35rem' }}>Round</th>
                <th style={{ padding: '0.35rem' }}>Game</th>
                <th style={{ padding: '0.35rem' }}>1-0</th>
                <th style={{ padding: '0.35rem' }}>0-1</th>
                <th style={{ padding: '0.35rem' }}>½-½</th>
              </tr>
            </thead>
            <tbody>
              {data.games.map((g) => (
                <tr key={g.game_id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '0.35rem', whiteSpace: 'nowrap' }}>{g.round_name}</td>
                  <td style={{ padding: '0.35rem' }}>
                    {g.white_player} — {g.black_player}
                  </td>
                  <td style={{ padding: '0.35rem' }}>{g.counts['1-0'] ?? 0}</td>
                  <td style={{ padding: '0.35rem' }}>{g.counts['0-1'] ?? 0}</td>
                  <td style={{ padding: '0.35rem' }}>{g.counts['1/2-1/2'] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
