export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
};

export class ApiClient {
  constructor(private readonly baseUrl = '/api/v1') {}

  async get<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
    return this.request<TResponse>(path, { ...init, method: 'GET' });
  }

  async request<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
    const { body, headers, ...init } = options;
    const isFormData = body instanceof FormData;
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(body === undefined || isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...headers,
      },
      body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
    });

    if (!response.ok) {
      throw new ApiError(response.status, await readErrorMessage(response));
    }

    if (response.status === 204) {
      return undefined as TResponse;
    }

    return (await response.json()) as TResponse;
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  const text = await response.text();
  if (text.length > 0) {
    return text;
  }
  return `Request failed with status ${response.status}`;
}

export const apiClient = new ApiClient();
