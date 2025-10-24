export interface SSEClientConfig {
  url: string;
  onMessage: (event: MessageEvent) => void;
  onError?: (error: Event) => void;
  onOpen?: (event: Event) => void;
  headers?: Record<string, string>;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private config: SSEClientConfig;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;
  private readonly reconnectDelay = 1000;

  constructor(config: SSEClientConfig) {
    this.config = config;
  }

  connect() {
    if (this.eventSource) {
      return;
    }

    try {
      // Note: EventSource doesn't support custom headers in browsers
      // For custom headers, you would need to use a polyfill or server-side implementation
      this.eventSource = new EventSource(this.config.url);

      this.eventSource.onmessage = (event) => {
        this.reconnectAttempts = 0;
        this.config.onMessage(event);
      };

      this.eventSource.onerror = (event) => {
        if (this.config.onError) {
          this.config.onError(event);
        }

        // Attempt to reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          setTimeout(() => {
            this.disconnect();
            this.connect();
          }, this.reconnectDelay * this.reconnectAttempts);
        }
      };

      this.eventSource.onopen = (event) => {
        this.reconnectAttempts = 0;
        if (this.config.onOpen) {
          this.config.onOpen(event);
        }
      };
    } catch (error) {
      console.error("Error creating SSE connection:", error);
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  isConnected(): boolean {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
  }
}
