const API_URL = import.meta.env.VITE_API_URL ?? '/api'
const TOKEN_KEY = 'quiniela_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(
  path: string,
  options: RequestInit & { json?: unknown } = {}
): Promise<T> {
  const { json, ...init } = options
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
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
    body: json !== undefined ? JSON.stringify(json) : init.body,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  return res.json()
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
    get: (id: number) =>
      request<{
        id: number
        name: string
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
      }>(`/tournaments/${id}`),
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
  },
  games: {
    updateResult: (gameId: number, result: '1-0' | '0-1' | '1/2-1/2') =>
      request<{ id: number; result: string }>(`/games/${gameId}`, {
        method: 'PATCH',
        json: { result },
      }),
  },
}
