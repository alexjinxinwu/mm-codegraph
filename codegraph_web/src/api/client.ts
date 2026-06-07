export class ApiError extends Error {
  status: number
  body: string

  constructor(status: number, body: string) {
    super(`HTTP ${status}: ${body}`)
    this.status = status
    this.body = body
  }
}

export async function apiGet(path: string): Promise<Response> {
  return fetch(path)
}
