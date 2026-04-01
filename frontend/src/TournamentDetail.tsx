import { useEffect, useState } from 'react'
import { api, type TournamentDetailPayload, type TournamentPlayer } from './api'

type Tournament = TournamentDetailPayload

type Prediction = { game_id: number; predicted_result: string }

const baseStyles = {
  container: { maxWidth: 640, margin: '4rem auto', fontFamily: 'system-ui' as const },
  btn: {
    padding: '0.25rem 0.5rem',
    fontSize: '0.875rem',
    border: '1px solid #999',
    borderRadius: 4,
    background: 'transparent',
    cursor: 'pointer' as const,
  },
  roundHeader: {
    padding: '0.75rem 1rem',
    marginBottom: '0.5rem',
    border: '1px solid #e5e4e7',
    borderRadius: 4,
    background: '#fff',
    cursor: 'pointer' as const,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
}

/** US Eastern Time (handles EST/EDT) for display and admin deadline inputs. */
const DEADLINE_DISPLAY_TZ = 'America/New_York'

function getEasternWallParts(d: Date): {
  y: number
  mo: number
  d: number
  h: number
  min: number
} {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: DEADLINE_DISPLAY_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
  const p = fmt.formatToParts(d)
  const get = (type: Intl.DateTimeFormatPart['type']) =>
    p.find((x) => x.type === type)?.value ?? ''
  return {
    y: parseInt(get('year'), 10),
    mo: parseInt(get('month'), 10),
    d: parseInt(get('day'), 10),
    h: parseInt(get('hour'), 10),
    min: parseInt(get('minute'), 10),
  }
}

/** Instant → `YYYY-MM-DDTHH:mm` for `<input type="datetime-local">` (values mean Eastern wall time). */
function isoToEasternDatetimeLocal(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const p = getEasternWallParts(d)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${p.y}-${pad(p.mo)}-${pad(p.d)}T${pad(p.h)}:${pad(p.min)}`
}

/**
 * Parse `YYYY-MM-DDTHH:mm` (optional seconds) as Eastern wall time → UTC ISO string.
 */
function easternDatetimeLocalToIso(naive: string): string | null {
  const m = naive.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/)
  if (!m) return null
  const y = +m[1]
  const mo = +m[2]
  const d = +m[3]
  const h = +m[4]
  const min = +m[5]
  if (mo < 1 || mo > 12 || d < 1 || d > 31 || h > 23 || min > 59) return null
  const utcMidnightGuess = Date.UTC(y, mo - 1, d, 0, 0)
  const start = utcMidnightGuess - 12 * 60 * 60 * 1000
  const end = utcMidnightGuess + 36 * 60 * 60 * 1000
  const matches: Date[] = []
  for (let t = start; t <= end; t += 60 * 1000) {
    const utc = new Date(t)
    const parts = getEasternWallParts(utc)
    if (parts.y === y && parts.mo === mo && parts.d === d && parts.h === h && parts.min === min) {
      matches.push(utc)
    }
  }
  if (matches.length === 0) return null
  return matches[0].toISOString()
}

function formatDeadline(iso: string) {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString('en-US', {
      timeZone: DEADLINE_DISPLAY_TZ,
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZoneName: 'short',
    })
  } catch {
    return iso
  }
}

const RESULT_OPTIONS = ['1-0', '0-1', '1/2-1/2'] as const

interface TournamentDetailProps {
  tournamentId: number
  isAdmin: boolean
  onBack: () => void
  onLeaderboard: () => void
  /** Opens aggregate prediction counts per game (all signed-in users). */
  onStatistics?: () => void
  /** After an admin deletes the tournament (navigate away). */
  onTournamentDeleted?: () => void
  onLogout?: () => void
}

function defaultPlayerOrder(players: TournamentPlayer[]): number[] {
  return [...players]
    .sort((a, b) => a.name_key.localeCompare(b.name_key))
    .map((p) => p.id)
}

function moveOrder(ids: number[], index: number, delta: number): number[] {
  const j = index + delta
  if (j < 0 || j >= ids.length) return ids
  const next = [...ids]
  const tmp = next[index]
  next[index] = next[j]
  next[j] = tmp
  return next
}

const reorderArrowBtnStyle = (disabled: boolean) =>
  ({
    ...baseStyles.btn,
    minWidth: '2.25rem',
    padding: '0.3rem 0.45rem',
    flexShrink: 0,
    opacity: disabled ? 0.4 : 1,
    cursor: disabled ? ('not-allowed' as const) : ('pointer' as const),
    color: disabled ? '#888' : '#333',
    borderColor: disabled ? '#ccc' : '#999',
  }) as const

function ReorderArrows({
  disableUp,
  disableDown,
  onUp,
  onDown,
}: {
  disableUp: boolean
  disableDown: boolean
  onUp: () => void
  onDown: () => void
}) {
  return (
    <span
      style={{
        display: 'inline-flex',
        gap: 6,
        flexShrink: 0,
        alignItems: 'center',
      }}
    >
      <button
        type="button"
        aria-label="Move up"
        disabled={disableUp}
        onClick={onUp}
        style={reorderArrowBtnStyle(disableUp)}
      >
        ↑
      </button>
      <button
        type="button"
        aria-label="Move down"
        disabled={disableDown}
        onClick={onDown}
        style={reorderArrowBtnStyle(disableDown)}
      >
        ↓
      </button>
    </span>
  )
}

export function TournamentDetail({
  tournamentId,
  isAdmin,
  onBack,
  onLeaderboard,
  onStatistics,
  onTournamentDeleted,
  onLogout,
}: TournamentDetailProps) {
  const [tournament, setTournament] = useState<Tournament | null>(null)
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [tableRankingIds, setTableRankingIds] = useState<number[] | null>(null)
  const [expandedRounds, setExpandedRounds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const toggleRound = (roundId: number) => {
    setExpandedRounds((prev) => {
      const next = new Set(prev)
      if (next.has(roundId)) next.delete(roundId)
      else next.add(roundId)
      return next
    })
  }

  const refresh = () => {
    return Promise.all([
      api.tournaments.get(tournamentId),
      api.predictions.list({ tournament_id: tournamentId }),
      api.tournaments.getTablePrediction(tournamentId),
    ])
      .then(([t, preds, table]) => {
        setTournament(t)
        setPredictions(preds)
        setTableRankingIds(table.ranking_player_ids ?? null)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [tournamentId])

  const savePrediction = async (
    gameId: number,
    result: '1-0' | '0-1' | '1/2-1/2',
  ): Promise<boolean> => {
    try {
      await api.predictions.create(gameId, result)
      setPredictions((prev) => {
        const filtered = prev.filter((p) => p.game_id !== gameId)
        return [...filtered, { game_id: gameId, predicted_result: result }]
      })
      return true
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
      return false
    }
  }

  const getPrediction = (gameId: number) =>
    predictions.find((p) => p.game_id === gameId)?.predicted_result ?? null

  const handleDeleteTournament = async () => {
    if (
      !confirm(
        'Delete this tournament and all rounds, games, predictions, and related data? This cannot be undone.'
      )
    ) {
      return
    }
    try {
      await api.tournaments.delete(tournamentId)
      onTournamentDeleted?.()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete tournament')
    }
  }

  const handleDeleteRound = async (roundId: number) => {
    if (
      !confirm(
        'Delete this round and all its games and predictions? This cannot be undone.'
      )
    ) {
      return
    }
    try {
      await api.tournaments.deleteRound(tournamentId, roundId)
      setExpandedRounds((prev) => {
        const next = new Set(prev)
        next.delete(roundId)
        return next
      })
      await refresh()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete round')
    }
  }

  if (loading) return <div style={baseStyles.container}>Loading…</div>
  if (error) return <div style={{ ...baseStyles.container, color: '#c00' }}>{error}</div>
  if (!tournament) return null

  return (
    <div style={baseStyles.container}>
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
          <button type="button" onClick={onBack} style={baseStyles.btn}>
            ← Back
          </button>
          <div style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto', flexShrink: 0 }}>
            <button type="button" onClick={onLeaderboard} style={baseStyles.btn}>
              Leaderboard
            </button>
            {onStatistics && (
              <button type="button" onClick={onStatistics} style={baseStyles.btn}>
                Statistics
              </button>
            )}
            {isAdmin && (
              <button
                type="button"
                onClick={() => void handleDeleteTournament()}
                style={{
                  ...baseStyles.btn,
                  color: '#a00',
                  borderColor: '#c77',
                }}
              >
                Delete tournament
              </button>
            )}
            {onLogout && (
              <button type="button" onClick={onLogout} style={baseStyles.btn}>
                Sign out
              </button>
            )}
          </div>
        </div>
        <h1 style={{ fontSize: '1.5rem', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{tournament.name}</h1>
      </div>

      {isAdmin && (
        <AdminScoringPanel
          tournamentId={tournamentId}
          pointsWhiteWin={tournament.points_white_win ?? 1}
          pointsBlackWin={tournament.points_black_win ?? 1}
          pointsDraw={tournament.points_draw ?? 1}
          onSaved={refresh}
        />
      )}

      {isAdmin && (
        <AdminTablePanel
          tournamentId={tournamentId}
          players={tournament.players}
          pointsTablePerRank={tournament.points_table_per_rank ?? 1}
          tablePredictionDeadline={tournament.table_prediction_deadline}
          finalRankingPlayerIds={tournament.final_ranking_player_ids}
          onSaved={refresh}
        />
      )}

      <UserTablePredictionPanel
        tournamentId={tournamentId}
        players={tournament.players}
        tablePredictionDeadline={tournament.table_prediction_deadline}
        savedRankingIds={tableRankingIds}
        refreshTournament={refresh}
      />

      <h2 style={{ fontSize: '1.125rem', marginBottom: '0.75rem' }}>Rounds</h2>
      {tournament.rounds.map((r) => {
        const isExpanded = expandedRounds.has(r.id)
        const deadlinePassed = new Date(r.prediction_deadline) < new Date()
        return (
          <div key={r.id}>
            <div
              role="button"
              tabIndex={0}
              onClick={() => toggleRound(r.id)}
              onKeyDown={(e) => e.key === 'Enter' && toggleRound(r.id)}
              style={baseStyles.roundHeader}
            >
              <span style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                {r.round_name} — Deadline: {formatDeadline(r.prediction_deadline)}
                {deadlinePassed && (
                  <span style={{ color: '#999', marginLeft: '0.5rem' }}>(closed)</span>
                )}
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  flexShrink: 0,
                }}
              >
                {isAdmin && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      void handleDeleteRound(r.id)
                    }}
                    style={{
                      ...baseStyles.btn,
                      fontSize: '0.75rem',
                      padding: '0.2rem 0.45rem',
                      color: '#a00',
                      borderColor: '#c77',
                    }}
                  >
                    Delete round
                  </button>
                )}
                <span style={{ fontSize: '0.75rem', color: '#666' }}>
                  {isExpanded ? '▲' : '▼'}
                </span>
              </span>
            </div>
            {isExpanded && (
              <div style={{ marginLeft: '1rem', marginBottom: '1rem' }}>
                {isAdmin && (
                  <AdminRoundDeadline
                    roundId={r.id}
                    predictionDeadline={r.prediction_deadline}
                    onSaved={refresh}
                  />
                )}
                {r.games.map((g) => (
                  <GameRow
                    key={g.id}
                    game={g}
                    currentPrediction={getPrediction(g.id)}
                    onSave={savePrediction}
                    deadlinePassed={deadlinePassed}
                    isAdmin={isAdmin}
                    onResultUpdate={refresh}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function GameRow({
  game,
  currentPrediction,
  onSave,
  deadlinePassed,
  isAdmin,
  onResultUpdate,
}: {
  game: {
    id: number
    white_player: string
    black_player: string
    white_rating: number
    black_rating: number
    result: string | null
  }
  currentPrediction: string | null
  onSave: (gameId: number, result: '1-0' | '0-1' | '1/2-1/2') => Promise<boolean>
  deadlinePassed: boolean
  isAdmin: boolean
  onResultUpdate: () => void
}) {
  const [sel, setSel] = useState(currentPrediction)
  const [saving, setSaving] = useState(false)
  /** Set after a successful Save in this session; row is green while selection matches. */
  const [lastSavedSelection, setLastSavedSelection] = useState<string | null>(null)
  const canEdit = !deadlinePassed
  const savedHighlight =
    lastSavedSelection !== null && sel !== null && sel === lastSavedSelection
  useEffect(() => {
    setSel(currentPrediction)
  }, [currentPrediction])

  return (
    <div
      style={{
        padding: '0.75rem 1rem',
        marginBottom: '0.5rem',
        border: savedHighlight ? '1px solid #2d8f54' : '1px solid #eee',
        borderRadius: 4,
        background: savedHighlight ? '#e8f5ed' : '#fafafa',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        flexWrap: 'wrap',
        transition: 'background 0.2s ease, border-color 0.2s ease',
      }}
    >
      <span style={{ fontWeight: 600 }}>
        {game.white_player} ({game.white_rating})
      </span>

      {canEdit ? (
        <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
          {RESULT_OPTIONS.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => setSel(sel === opt ? null : opt)}
              style={{
                ...baseStyles.btn,
                padding: '0.35rem 0.6rem',
                fontSize: '0.875rem',
                background:
                  sel === opt ? (savedHighlight ? '#1f6b3d' : '#333') : '#fff',
                color: sel === opt ? '#fff' : '#333',
                borderColor: sel === opt ? (savedHighlight ? '#1f6b3d' : '#333') : '#ccc',
              }}
            >
              {opt}
            </button>
          ))}
        </div>
      ) : (
        currentPrediction && (
          <span style={{ fontSize: '0.875rem', color: '#666' }}>
            Your pick: {currentPrediction}
          </span>
        )
      )}

      <span style={{ fontWeight: 600 }}>
        {game.black_player} ({game.black_rating})
      </span>

      {canEdit && (
        <button
          type="button"
          disabled={saving || !sel}
          style={{
            ...baseStyles.btn,
            padding: '0.35rem 0.6rem',
            background: sel ? (savedHighlight ? '#1f6b3d' : '#333') : 'transparent',
            color: sel ? '#fff' : '#333',
            borderColor: sel ? (savedHighlight ? '#1f6b3d' : '#999') : '#999',
            marginLeft: 'auto',
            flexShrink: 0,
          }}
          onClick={async () => {
            if (!sel || !RESULT_OPTIONS.includes(sel as any)) return
            setSaving(true)
            try {
              const ok = await onSave(game.id, sel as '1-0' | '0-1' | '1/2-1/2')
              if (ok) setLastSavedSelection(sel)
            } finally {
              setSaving(false)
            }
          }}
        >
          {saving ? '…' : savedHighlight ? 'Saved' : 'Save'}
        </button>
      )}

      {game.result && !isAdmin && (
        <span style={{ fontSize: '0.8125rem', color: '#666' }}>
          Result: {game.result}
        </span>
      )}

      {isAdmin && deadlinePassed && (
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginLeft: 'auto' }}>
          <span style={{ fontSize: '0.8125rem', color: '#666' }}>Result:</span>
          <AdminResultInput
            gameId={game.id}
            currentResult={game.result}
            onUpdate={onResultUpdate}
          />
        </div>
      )}
    </div>
  )
}

function AdminResultInput({
  gameId,
  currentResult,
  onUpdate,
}: {
  gameId: number
  currentResult: string | null
  onUpdate: () => void
}) {
  const [result, setResult] = useState(currentResult ?? '')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setResult(currentResult ?? '')
  }, [currentResult])

  const handleSave = async () => {
    const r = result.trim()
    if (!r || !RESULT_OPTIONS.includes(r as (typeof RESULT_OPTIONS)[number])) return
    setSaving(true)
    try {
      const res = await api.games.updateResult(gameId, r as '1-0' | '0-1' | '1/2-1/2')
      setResult(res.result ?? r)
      await onUpdate()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <div style={{ display: 'flex', gap: 2 }}>
        {RESULT_OPTIONS.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => setResult(result === opt ? '' : opt)}
            style={{
              ...baseStyles.btn,
              padding: '0.25rem 0.5rem',
              fontSize: '0.875rem',
              background: result === opt ? '#333' : '#fff',
              color: result === opt ? '#fff' : '#333',
              borderColor: result === opt ? '#333' : '#ccc',
            }}
          >
            {opt}
          </button>
        ))}
      </div>
      <button
        type="button"
        disabled={saving || !result}
        onClick={handleSave}
        style={{
          ...baseStyles.btn,
          padding: '0.25rem 0.5rem',
          background: result ? '#333' : 'transparent',
          color: result ? '#fff' : '#333',
        }}
      >
        {saving ? '…' : 'Set'}
      </button>
    </div>
  )
}

function AdminScoringPanel({
  tournamentId,
  pointsWhiteWin,
  pointsBlackWin,
  pointsDraw,
  onSaved,
}: {
  tournamentId: number
  pointsWhiteWin: number
  pointsBlackWin: number
  pointsDraw: number
  onSaved: () => void
}) {
  const [pw, setPw] = useState(String(pointsWhiteWin))
  const [pb, setPb] = useState(String(pointsBlackWin))
  const [pd, setPd] = useState(String(pointsDraw))
  const [saving, setSaving] = useState(false)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    setPw(String(pointsWhiteWin))
    setPb(String(pointsBlackWin))
    setPd(String(pointsDraw))
  }, [pointsWhiteWin, pointsBlackWin, pointsDraw])

  const handleSave = async () => {
    const a = parseInt(pw, 10)
    const b = parseInt(pb, 10)
    const c = parseInt(pd, 10)
    if ([a, b, c].some((n) => Number.isNaN(n) || n < 0)) {
      alert('Use non-negative whole numbers')
      return
    }
    setSaving(true)
    try {
      await api.tournaments.update(tournamentId, {
        points_white_win: a,
        points_black_win: b,
        points_draw: c,
      })
      await onSaved()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      style={{
        marginBottom: '1rem',
        border: '1px solid #e5e4e7',
        borderRadius: 4,
        overflow: 'hidden',
        background: '#fff',
      }}
    >
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded((v) => !v)}
        onKeyDown={(e) => e.key === 'Enter' && setExpanded((v) => !v)}
        style={{
          ...baseStyles.roundHeader,
          marginBottom: 0,
          border: 'none',
          borderRadius: 0,
        }}
      >
        <span style={{ fontSize: '1rem', fontWeight: 600 }}>Scoring</span>
        <span style={{ fontSize: '0.75rem', color: '#666' }}>{expanded ? '▲' : '▼'}</span>
      </div>
      {expanded && (
        <div style={{ padding: '0.75rem 1rem', background: '#fafafa', borderTop: '1px solid #e5e4e7' }}>
          <p style={{ fontSize: '0.8125rem', color: '#666', margin: '0 0 0.75rem 0' }}>
            Points for each correct prediction: white win (1-0), black win (0-1), draw (½-½).
          </p>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.75rem',
              alignItems: 'center',
            }}
          >
            <label style={{ fontSize: '0.875rem' }}>
              1-0{' '}
              <input
                type="number"
                min={0}
                value={pw}
                onChange={(e) => setPw(e.target.value)}
                style={{ width: 56, padding: '0.25rem', marginLeft: 4 }}
              />
            </label>
            <label style={{ fontSize: '0.875rem' }}>
              0-1{' '}
              <input
                type="number"
                min={0}
                value={pb}
                onChange={(e) => setPb(e.target.value)}
                style={{ width: 56, padding: '0.25rem', marginLeft: 4 }}
              />
            </label>
            <label style={{ fontSize: '0.875rem' }}>
              Draw{' '}
              <input
                type="number"
                min={0}
                value={pd}
                onChange={(e) => setPd(e.target.value)}
                style={{ width: 56, padding: '0.25rem', marginLeft: 4 }}
              />
            </label>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              style={{
                ...baseStyles.btn,
                padding: '0.35rem 0.75rem',
                background: '#333',
                color: '#fff',
              }}
            >
              {saving ? 'Saving…' : 'Save scoring'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function AdminRoundDeadline({
  roundId,
  predictionDeadline,
  onSaved,
}: {
  roundId: number
  predictionDeadline: string
  onSaved: () => void
}) {
  const [value, setValue] = useState(() => isoToEasternDatetimeLocal(predictionDeadline))
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setValue(isoToEasternDatetimeLocal(predictionDeadline))
  }, [predictionDeadline])

  const handleSave = async () => {
    if (!value) return
    const iso = easternDatetimeLocalToIso(value)
    if (!iso) {
      alert('Invalid date or time (use a valid calendar date in Eastern Time).')
      return
    }
    setSaving(true)
    try {
      await api.rounds.patch(roundId, { prediction_deadline: iso })
      await onSaved()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update deadline')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem',
        alignItems: 'center',
        marginBottom: '0.75rem',
        padding: '0.5rem 0.75rem',
        background: '#f5f5f5',
        borderRadius: 4,
        border: '1px solid #e5e4e7',
      }}
    >
      <span style={{ fontSize: '0.8125rem', color: '#555' }}>
        Prediction deadline <span style={{ color: '#888' }}>(Eastern Time)</span>
      </span>
      <input
        type="datetime-local"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        style={{
          padding: '0.25rem 0.5rem',
          fontSize: '0.875rem',
          border: '1px solid #ccc',
          borderRadius: 4,
        }}
      />
      <button
        type="button"
        onClick={handleSave}
        disabled={saving || !value}
        style={{
          ...baseStyles.btn,
          padding: '0.25rem 0.5rem',
          background: value ? '#333' : '#ccc',
          color: '#fff',
        }}
      >
        {saving ? 'Saving…' : 'Save deadline'}
      </button>
    </div>
  )
}

function playerNameById(players: TournamentPlayer[], id: number): string {
  return players.find((p) => p.id === id)?.name ?? `#${id}`
}

function UserTablePredictionPanel({
  tournamentId,
  players,
  tablePredictionDeadline,
  savedRankingIds,
  refreshTournament,
}: {
  tournamentId: number
  players: TournamentPlayer[]
  tablePredictionDeadline: string | null
  savedRankingIds: number[] | null
  refreshTournament: () => Promise<void>
}) {
  const [order, setOrder] = useState<number[]>([])
  const [saving, setSaving] = useState(false)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (!players.length) {
      setOrder([])
      return
    }
    const ids = new Set(players.map((p) => p.id))
    if (
      savedRankingIds &&
      savedRankingIds.length === players.length &&
      savedRankingIds.every((id) => ids.has(id))
    ) {
      setOrder(savedRankingIds)
    } else {
      setOrder(defaultPlayerOrder(players))
    }
  }, [players, savedRankingIds])

  if (!players.length) return null

  const deadlinePassed =
    tablePredictionDeadline != null && new Date(tablePredictionDeadline) < new Date()
  const canPredict =
    tablePredictionDeadline != null && !deadlinePassed

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded((e) => !e)}
        onKeyDown={(e) => e.key === 'Enter' && setExpanded((ex) => !ex)}
        style={baseStyles.roundHeader}
      >
        <span style={{ fontSize: '1.05rem', fontWeight: 600 }}>
          Final table prediction
          {tablePredictionDeadline && (
            <span style={{ fontWeight: 400, color: '#555' }}>
              {' '}
              — Deadline: {formatDeadline(tablePredictionDeadline)}
            </span>
          )}
          {deadlinePassed && (
            <span style={{ color: '#999', marginLeft: '0.35rem', fontWeight: 400 }}>(closed)</span>
          )}
        </span>
        <span style={{ fontSize: '0.75rem', color: '#666' }}>{expanded ? '▲' : '▼'}</span>
      </div>
      {expanded && (
        <div
          style={{
            marginLeft: '0.25rem',
            marginBottom: '0.75rem',
            padding: '0.75rem 1rem',
            border: '1px solid #e5e4e7',
            borderTop: 'none',
            borderRadius: '0 0 4px 4px',
            background: '#fff',
          }}
        >
          <p style={{ fontSize: '0.8125rem', color: '#666', marginBottom: '0.75rem' }}>
            Order players from first place to last. Points per correct rank are set by the admin.
          </p>
          {!tablePredictionDeadline && (
            <p style={{ fontSize: '0.875rem', color: '#a60' }}>The admin has not opened table predictions yet.</p>
          )}
          {tablePredictionDeadline && deadlinePassed && (
            <p style={{ fontSize: '0.875rem', color: '#666' }}>Table prediction is closed.</p>
          )}
          {canPredict && (
            <>
              <ol
                style={{
                  margin: '0 0 0.75rem 0',
                  paddingLeft: '1.5rem',
                  listStylePosition: 'outside',
                }}
              >
                {order.map((pid, idx) => (
                  <li
                    key={pid}
                    style={{
                      marginBottom: '0.45rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      flexWrap: 'nowrap',
                    }}
                  >
                    <span
                      style={{
                        flex: 1,
                        minWidth: 0,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {playerNameById(players, pid)}
                    </span>
                    <ReorderArrows
                      disableUp={idx === 0}
                      disableDown={idx === order.length - 1}
                      onUp={() => setOrder((o) => moveOrder(o, idx, -1))}
                      onDown={() => setOrder((o) => moveOrder(o, idx, 1))}
                    />
                  </li>
                ))}
              </ol>
              <button
                type="button"
                disabled={saving}
                onClick={async () => {
                  setSaving(true)
                  try {
                    await api.tournaments.saveTablePrediction(tournamentId, order)
                    await refreshTournament()
                  } catch (err) {
                    alert(err instanceof Error ? err.message : 'Failed to save')
                  } finally {
                    setSaving(false)
                  }
                }}
                style={{
                  ...baseStyles.btn,
                  padding: '0.35rem 0.75rem',
                  background: '#333',
                  color: '#fff',
                }}
              >
                {saving ? 'Saving…' : 'Save table prediction'}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function AdminTablePanel({
  tournamentId,
  players,
  pointsTablePerRank,
  tablePredictionDeadline,
  finalRankingPlayerIds,
  onSaved,
}: {
  tournamentId: number
  players: TournamentPlayer[]
  pointsTablePerRank: number
  tablePredictionDeadline: string | null
  finalRankingPlayerIds: number[] | null
  onSaved: () => void
}) {
  const [deadlineLocal, setDeadlineLocal] = useState('')
  const [ptr, setPtr] = useState(String(pointsTablePerRank))
  const [finalOrder, setFinalOrder] = useState<number[]>([])
  const [savingDeadline, setSavingDeadline] = useState(false)
  const [savingPtr, setSavingPtr] = useState(false)
  const [savingFinal, setSavingFinal] = useState(false)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    setPtr(String(pointsTablePerRank))
  }, [pointsTablePerRank])

  useEffect(() => {
    setDeadlineLocal(
      tablePredictionDeadline ? isoToEasternDatetimeLocal(tablePredictionDeadline) : ''
    )
  }, [tablePredictionDeadline])

  useEffect(() => {
    if (!players.length) {
      setFinalOrder([])
      return
    }
    const ids = new Set(players.map((p) => p.id))
    if (
      finalRankingPlayerIds &&
      finalRankingPlayerIds.length === players.length &&
      finalRankingPlayerIds.every((id) => ids.has(id))
    ) {
      setFinalOrder(finalRankingPlayerIds)
    } else {
      setFinalOrder(defaultPlayerOrder(players))
    }
  }, [players, finalRankingPlayerIds])

  if (!players.length) return null

  return (
    <div style={{ marginBottom: '1rem' }}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded((e) => !e)}
        onKeyDown={(e) => e.key === 'Enter' && setExpanded((ex) => !ex)}
        style={{
          ...baseStyles.roundHeader,
          borderColor: '#c4a574',
          background: '#fffef8',
        }}
      >
        <span style={{ fontSize: '1.05rem', fontWeight: 600 }}>Table prediction (admin)</span>
        <span style={{ fontSize: '0.75rem', color: '#666' }}>{expanded ? '▲' : '▼'}</span>
      </div>
      {expanded && (
    <div
      style={{
        padding: '0.75rem 1rem',
        border: '1px solid #c4a574',
        borderTop: 'none',
        borderRadius: '0 0 4px 4px',
        background: '#fffef8',
      }}
    >

      <div style={{ marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '0.8125rem', color: '#555', marginRight: '0.5rem' }}>
          Table prediction deadline <span style={{ color: '#888' }}>(Eastern Time)</span>
        </span>
        <input
          type="datetime-local"
          value={deadlineLocal}
          onChange={(e) => setDeadlineLocal(e.target.value)}
          style={{ padding: '0.25rem 0.5rem', fontSize: '0.875rem', borderRadius: 4, border: '1px solid #ccc' }}
        />
        <button
          type="button"
          disabled={savingDeadline || !deadlineLocal}
          onClick={async () => {
            const iso = easternDatetimeLocalToIso(deadlineLocal)
            if (!iso) {
              alert('Invalid date or time (use a valid calendar date in Eastern Time).')
              return
            }
            setSavingDeadline(true)
            try {
              await api.tournaments.update(tournamentId, {
                table_prediction_deadline: iso,
              })
              await onSaved()
            } catch (err) {
              alert(err instanceof Error ? err.message : 'Failed')
            } finally {
              setSavingDeadline(false)
            }
          }}
          style={{ ...baseStyles.btn, marginLeft: '0.5rem', background: '#333', color: '#fff' }}
        >
          {savingDeadline ? '…' : 'Save deadline'}
        </button>
      </div>

      <div style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <label style={{ fontSize: '0.875rem' }}>
          Points per correct rank{' '}
          <input
            type="number"
            min={0}
            value={ptr}
            onChange={(e) => setPtr(e.target.value)}
            style={{ width: 56, padding: '0.25rem', marginLeft: 4 }}
          />
        </label>
        <button
          type="button"
          disabled={savingPtr}
          onClick={async () => {
            const n = parseInt(ptr, 10)
            if (Number.isNaN(n) || n < 0) {
              alert('Invalid number')
              return
            }
            setSavingPtr(true)
            try {
              await api.tournaments.update(tournamentId, { points_table_per_rank: n })
              await onSaved()
            } catch (err) {
              alert(err instanceof Error ? err.message : 'Failed')
            } finally {
              setSavingPtr(false)
            }
          }}
          style={{ ...baseStyles.btn, background: '#333', color: '#fff' }}
        >
          {savingPtr ? '…' : 'Save'}
        </button>
      </div>

      <div>
        <p style={{ fontSize: '0.8125rem', color: '#666', marginBottom: '0.5rem' }}>
          Final standings (actual result — used for leaderboard table points)
        </p>
        <ol
          style={{
            margin: '0 0 0.75rem 0',
            paddingLeft: '1.5rem',
            listStylePosition: 'outside',
          }}
        >
          {finalOrder.map((pid, idx) => (
            <li
              key={pid}
              style={{
                marginBottom: '0.45rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                flexWrap: 'nowrap',
              }}
            >
              <span
                style={{
                  flex: 1,
                  minWidth: 0,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {playerNameById(players, pid)}
              </span>
              <ReorderArrows
                disableUp={idx === 0}
                disableDown={idx === finalOrder.length - 1}
                onUp={() => setFinalOrder((o) => moveOrder(o, idx, -1))}
                onDown={() => setFinalOrder((o) => moveOrder(o, idx, 1))}
              />
            </li>
          ))}
        </ol>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            disabled={savingFinal}
            onClick={async () => {
              setSavingFinal(true)
              try {
                await api.tournaments.update(tournamentId, {
                  final_ranking_player_ids: finalOrder,
                })
                await onSaved()
              } catch (err) {
                alert(err instanceof Error ? err.message : 'Failed')
              } finally {
                setSavingFinal(false)
              }
            }}
            style={{ ...baseStyles.btn, background: '#333', color: '#fff' }}
          >
            {savingFinal ? '…' : 'Save final ranking'}
          </button>
          <button
            type="button"
            disabled={savingFinal}
            onClick={async () => {
              setSavingFinal(true)
              try {
                await api.tournaments.update(tournamentId, {
                  final_ranking_player_ids: null,
                })
                await onSaved()
              } catch (err) {
                alert(err instanceof Error ? err.message : 'Failed')
              } finally {
                setSavingFinal(false)
              }
            }}
            style={baseStyles.btn}
          >
            Clear ranking
          </button>
        </div>
      </div>
    </div>
      )}
    </div>
  )
}

