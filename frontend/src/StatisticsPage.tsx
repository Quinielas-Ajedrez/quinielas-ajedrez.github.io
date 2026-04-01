/**
 * Per-tournament view: how many users picked each result per board (aggregate counts).
 *
 * Future: replace or supplement the table with plots (bar/stacked charts per game,
 * distribution across rounds, etc.) once a chart library is chosen.
 */

import { useEffect, useMemo, useState } from 'react'
import { api } from './api'

type StatGame = {
  game_id: number
  white_player: string
  black_player: string
  round_name: string
  counts: Record<string, number>
}

function groupGamesByRound(games: StatGame[]): { roundName: string; games: StatGame[] }[] {
  const order: string[] = []
  const map = new Map<string, StatGame[]>()
  for (const g of games) {
    if (!map.has(g.round_name)) {
      map.set(g.round_name, [])
      order.push(g.round_name)
    }
    map.get(g.round_name)!.push(g)
  }
  return order.map((roundName) => ({ roundName, games: map.get(roundName)! }))
}

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
  const [data, setData] = useState<{ games: StatGame[] } | null>(null)
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

  const rounds = useMemo(() => (data ? groupGamesByRound(data.games) : []), [data])

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
          Prediction counts per game, grouped by round (how many users chose each result).
        </p>
      </div>

      {loading && <p style={{ color: '#666' }}>Loading…</p>}
      {err && <p style={{ color: '#c00' }}>{err}</p>}
      {data && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {rounds.map(({ roundName, games }, idx) => (
            <section
              key={`${roundName}-${idx}`}
              style={{
                border: '1px solid #e5e4e7',
                borderRadius: 4,
                background: '#fff',
                overflow: 'hidden',
              }}
            >
              <h2
                style={{
                  fontSize: '1.0625rem',
                  margin: 0,
                  padding: '0.65rem 0.75rem',
                  background: '#fafafa',
                  borderBottom: '1px solid #e5e4e7',
                  fontWeight: 600,
                }}
              >
                {roundName}
              </h2>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', borderBottom: '1px solid #eee' }}>
                      <th style={{ padding: '0.4rem 0.75rem' }}>Game</th>
                      <th style={{ padding: '0.4rem 0.5rem' }}>1-0</th>
                      <th style={{ padding: '0.4rem 0.5rem' }}>0-1</th>
                      <th style={{ padding: '0.4rem 0.75rem 0.4rem 0.5rem' }}>½-½</th>
                    </tr>
                  </thead>
                  <tbody>
                    {games.map((g) => (
                      <tr key={g.game_id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                        <td style={{ padding: '0.4rem 0.75rem' }}>
                          {g.white_player} — {g.black_player}
                        </td>
                        <td style={{ padding: '0.4rem 0.5rem' }}>{g.counts['1-0'] ?? 0}</td>
                        <td style={{ padding: '0.4rem 0.5rem' }}>{g.counts['0-1'] ?? 0}</td>
                        <td style={{ padding: '0.4rem 0.75rem 0.4rem 0.5rem' }}>
                          {g.counts['1/2-1/2'] ?? 0}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
