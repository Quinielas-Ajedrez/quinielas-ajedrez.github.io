/** Use `||` so empty `VITE_API_URL=""` still defaults to `/api` (see Vite base URL). */
const API_URL = import.meta.env.VITE_API_URL || '/api'
const TOKEN_KEY = 'quiniela_token'
const GATE_TOKEN_KEY = 'quiniela_gate_token'

/** Must match backend `GATE_HEADER_NAME`. */
export const GATE_HEADER_NAME = 'X-Quiniela-Gate'

export function getGateToken(): string | null {
  try {
    return sessionStorage.getItem(GATE_TOKEN_KEY)
  } catch {
    return null
  }
}

export function setGateToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(GATE_TOKEN_KEY, token)
    else sessionStorage.removeItem(GATE_TOKEN_KEY)
  } catch {
    /* sessionStorage unavailable */
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((e) =>
        e && typeof e === 'object' && 'msg' in e ? String((e as { msg: unknown }).msg) : JSON.stringify(e)
      )
      .join(' ')
  }
  return fallback
}

async function request<T>(
  path: string,
  options: RequestInit & { json?: unknown; skipJson?: boolean } = {}
): Promise<T> {
  const { json, skipJson = false, ...init } = options
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  }
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const gate = getGateToken()
  if (gate) {
    headers[GATE_HEADER_NAME] = gate
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
    body: json !== undefined ? JSON.stringify(json) : init.body,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detailMessage(err.detail, res.statusText || 'Request failed'))
  }
  if (skipJson || res.status === 204) {
    return undefined as T
  }
  return res.json()
}

export type TournamentPlayer = { id: number; name: string; name_key: string }

export type TournamentDetailPayload = {
  id: number
  name: string
  points_white_win: number
  points_black_win: number
  points_draw: number
  points_table_per_rank: number
  table_prediction_deadline: string | null
  final_ranking_player_ids: number[] | null
  players: TournamentPlayer[]
  rounds: {
    id: number
    round_number: number
    round_name: string
    prediction_deadline: string
    games: {
      id: number
      white_player: string
      black_player: string
      white_rating: number
      black_rating: number
      result: string | null
    }[]
  }[]
}

export const api = {
  auth: {
    login: (username: string, password: string) =>
      request<{ access_token: string }>('/auth/login', {
        method: 'POST',
        json: { username, password },
      }),
    register: (name: string, username: string, password: string) =>
      request<{ id: number; name: string; username: string; is_admin: boolean }>(
        '/auth/register',
        { method: 'POST', json: { name, username, password } }
      ),
    me: () =>
      request<{ id: number; name: string; username: string; is_admin: boolean; is_super_admin: boolean }>(
        '/auth/me'
      ),
  },
  tournaments: {
    list: () =>
      request<{ id: number; name: string }[]>('/tournaments'),
    import: (yaml_content: string) =>
      request<{ id: number; name: string; rounds: unknown[] }>('/tournaments/import', {
        method: 'POST',
        json: { yaml_content },
      }),
    get: (id: number) => request<TournamentDetailPayload>(`/tournaments/${id}`),
    update: (
      id: number,
      body: {
        name?: string
        yaml_content?: string
        points_white_win?: number
        points_black_win?: number
        points_draw?: number
        points_table_per_rank?: number
        table_prediction_deadline?: string | null
        final_ranking_player_ids?: number[] | null
      }
    ) => request<TournamentDetailPayload>(`/tournaments/${id}`, { method: 'PUT', json: body }),
    getTablePrediction: (tournamentId: number) =>
      request<{ ranking_player_ids: number[] | null }>(
        `/tournaments/${tournamentId}/table-prediction`
      ),
    saveTablePrediction: (tournamentId: number, ranking_player_ids: number[]) =>
      request<{ ranking_player_ids: number[] }>(
        `/tournaments/${tournamentId}/table-prediction`,
        { method: 'POST', json: { ranking_player_ids } }
      ),
    predictionStatistics: (tournamentId: number) =>
      request<{
        games: {
          game_id: number
          white_player: string
          black_player: string
          round_name: string
          counts: Record<string, number>
        }[]
      }>(`/tournaments/${tournamentId}/prediction-statistics`),
    /**
     * POST /…/delete first (some proxies block DELETE). If that route is missing (404 Not Found),
     * fall back to DELETE /…/{id}. If the API process is stale, DELETE returns 405 Method Not Allowed
     * because only GET is registered for that path — restart uvicorn with the current backend code.
     */
    delete: async (id: number) => {
      try {
        await request<void>(`/tournaments/${id}/delete`, { method: 'POST', skipJson: true })
        return
      } catch (e) {
        if (!(e instanceof Error) || e.message !== 'Not Found') throw e
      }
      try {
        await request<void>(`/tournaments/${id}`, { method: 'DELETE', skipJson: true })
      } catch (e2) {
        const m = e2 instanceof Error ? e2.message : ''
        if (m === 'Method Not Allowed' || m.includes('Not Allowed')) {
          throw new Error(
            'The API server is running old code without tournament delete routes. Stop uvicorn and start it again from the project root: uv run uvicorn backend.main:app --reload'
          )
        }
        throw e2
      }
    },
    deleteRound: async (tournamentId: number, roundId: number) => {
      try {
        await request<void>(`/tournaments/${tournamentId}/rounds/${roundId}/delete`, {
          method: 'POST',
          skipJson: true,
        })
        return
      } catch (e) {
        if (!(e instanceof Error) || e.message !== 'Not Found') throw e
      }
      try {
        await request<void>(`/tournaments/${tournamentId}/rounds/${roundId}`, {
          method: 'DELETE',
          skipJson: true,
        })
      } catch (e2) {
        const m = e2 instanceof Error ? e2.message : ''
        if (m === 'Method Not Allowed' || m.includes('Not Allowed')) {
          throw new Error(
            'The API server is running old code without round delete routes. Stop uvicorn and start it again from the project root: uv run uvicorn backend.main:app --reload'
          )
        }
        throw e2
      }
    },
  },
  predictions: {
    create: (game_id: number, predicted_result: '1-0' | '0-1' | '1/2-1/2') =>
      request<{ id: number; user_id: number; game_id: number; predicted_result: string }>(
        '/predictions',
        { method: 'POST', json: { game_id, predicted_result } }
      ),
    list: (params: { round_id?: number; tournament_id?: number }) => {
      const q = new URLSearchParams()
      if (params.round_id != null) q.set('round_id', String(params.round_id))
      if (params.tournament_id != null) q.set('tournament_id', String(params.tournament_id))
      return request<{ id: number; user_id: number; game_id: number; predicted_result: string }[]>(
        `/predictions?${q}`
      )
    },
  },
  leaderboard: {
    get: (tournamentId: number) =>
      request<{ entries: { user_id: number; username: string; name: string; points: number }[] }>(
        `/tournaments/${tournamentId}/leaderboard`
      ),
  },
  users: {
    list: () =>
      request<{ id: number; name: string; username: string; is_admin: boolean; is_super_admin: boolean }[]>(
        '/users'
      ),
    updateAdmin: (userId: number, isAdmin: boolean) =>
      request<{ id: number; name: string; username: string; is_admin: boolean; is_super_admin: boolean }>(
        `/users/${userId}`,
        { method: 'PATCH', json: { is_admin: isAdmin } }
      ),
    /** POST …/delete first; falls back to DELETE (see tournaments.delete). */
    delete: async (userId: number) => {
      try {
        await request<void>(`/users/${userId}/delete`, { method: 'POST', skipJson: true })
        return
      } catch (e) {
        if (!(e instanceof Error) || e.message !== 'Not Found') throw e
      }
      try {
        await request<void>(`/users/${userId}`, { method: 'DELETE', skipJson: true })
      } catch (e2) {
        const m = e2 instanceof Error ? e2.message : ''
        if (m === 'Method Not Allowed' || m.includes('Not Allowed')) {
          throw new Error(
            'User delete is not available on this API. Restart uvicorn with the latest backend code.'
          )
        }
        throw e2
      }
    },
  },
  games: {
    updateResult: (gameId: number, result: '1-0' | '0-1' | '1/2-1/2') =>
      request<{ id: number; result: string }>(`/games/${gameId}`, {
        method: 'PATCH',
        json: { result },
      }),
  },
  rounds: {
    patch: (
      roundId: number,
      body: { round_name?: string; prediction_deadline?: string }
    ) =>
      request<{ id: number; round_name: string; prediction_deadline: string }>(`/rounds/${roundId}`, {
        method: 'PATCH',
        json: body,
      }),
  },
}
