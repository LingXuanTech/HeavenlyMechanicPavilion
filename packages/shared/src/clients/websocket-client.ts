export interface WebSocketClientConfig {
  url: string;
  onMessage: (data: unknown) => void;
  onError?: (error: Event) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  reconnect?: boolean;
  protocols?: string | string[];
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: WebSocketClientConfig;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;
  private readonly reconnectDelay = 1000;
  private shouldReconnect: boolean;

  constructor(config: WebSocketClientConfig) {
    this.config = config;
    this.shouldReconnect = config.reconnect ?? true;
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.config.url, this.config.protocols);

      this.ws.onopen = (event) => {
        this.reconnectAttempts = 0;
        if (this.config.onOpen) {
          this.config.onOpen(event);
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.config.onMessage(data);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
          this.config.onMessage(event.data);
        }
      };

      this.ws.onerror = (event) => {
        if (this.config.onError) {
          this.config.onError(event);
        }
      };

      this.ws.onclose = (event) => {
        if (this.config.onClose) {
          this.config.onClose(event);
        }

        // Attempt to reconnect if enabled
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          setTimeout(() => {
            this.connect();
          }, this.reconnectDelay * this.reconnectAttempts);
        }
      };
    } catch (error) {
      console.error("Error creating WebSocket connection:", error);
    }
  }

  send(data: unknown) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === "string" ? data : JSON.stringify(data));
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
