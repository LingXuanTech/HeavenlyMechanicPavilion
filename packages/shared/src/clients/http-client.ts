export interface ClientConfig {
  baseUrl: string;
  apiKey?: string;
  headers?: Record<string, string>;
  fetch?: typeof fetch;
}

export class HttpClient {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;
  private readonly fetcher: typeof fetch;

  constructor(config: ClientConfig) {
    if (!config.baseUrl) {
      throw new Error("HttpClient requires a baseUrl");
    }

    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.headers = {
      "Content-Type": "application/json",
      ...(config.headers ?? {}),
      ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
    };
    this.fetcher = config.fetch ?? fetch;
  }

  private buildUrl(path: string) {
    const normalized = path.startsWith("/") ? path : `/${path}`;
    return `${this.baseUrl}${normalized}`;
  }

  async get<T>(path: string): Promise<T> {
    const response = await this.fetcher(this.buildUrl(path), {
      method: "GET",
      headers: this.headers,
    });
    if (!response.ok) {
      throw await this.toError(response);
    }
    return (await response.json()) as T;
  }

  async post<T, TBody = unknown>(path: string, body?: TBody): Promise<T> {
    const response = await this.fetcher(this.buildUrl(path), {
      method: "POST",
      headers: this.headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      throw await this.toError(response);
    }
    return (await response.json()) as T;
  }

  async stream(path: string, init?: RequestInit): Promise<Response> {
    const response = await this.fetcher(this.buildUrl(path), {
      method: "GET",
      headers: this.headers,
      ...init,
    });
    if (!response.ok) {
      throw await this.toError(response);
    }
    return response;
  }

  private async toError(response: Response): Promise<Error> {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload?.message) {
        message = payload.message;
      }
    } catch (error) {
      // ignore JSON parsing errors
    }
    const err = new Error(message);
    (err as Error & { status?: number }).status = response.status;
    return err;
  }
}
