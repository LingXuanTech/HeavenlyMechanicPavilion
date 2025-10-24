export type ColorScale = {
  50: string;
  100: string;
  200: string;
  300: string;
  400: string;
  500: string;
  600: string;
  700: string;
  800: string;
  900: string;
};

export type DesignTokens = {
  colors: {
    background: string;
    foreground: string;
    surface: string;
    surfaceMuted: string;
    border: string;
    ring: string;
    input: string;
    primary: string;
    primaryForeground: string;
    secondary: string;
    secondaryForeground: string;
    accent: string;
    accentForeground: string;
    muted: string;
    mutedForeground: string;
    destructive: string;
    destructiveForeground: string;
    warning: string;
    warningForeground: string;
    success: string;
    successForeground: string;
    info: string;
    infoForeground: string;
    gridline: string;
  };
  radii: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
    full: string;
  };
  spacing: {
    gutter: string;
    container: string;
  };
  shadows: {
    subtle: string;
    float: string;
    pop: string;
  };
  typography: {
    body: string;
    headings: string;
    mono: string;
  };
};

export const tradingAgentsTokens: DesignTokens = {
  colors: {
    background: "#050b14",
    foreground: "#f4fbf8",
    surface: "#0c1424",
    surfaceMuted: "#0f1d30",
    border: "#142a40",
    ring: "#1fe7b1",
    input: "#0f1d30",
    primary: "#14c290",
    primaryForeground: "#041810",
    secondary: "#1f2c45",
    secondaryForeground: "#d2f6ec",
    accent: "#57d2ff",
    accentForeground: "#02121b",
    muted: "#0b1726",
    mutedForeground: "#8aa7c8",
    destructive: "#ef476f",
    destructiveForeground: "#160208",
    warning: "#f59f00",
    warningForeground: "#1d1200",
    success: "#28d487",
    successForeground: "#04150d",
    info: "#3b82f6",
    infoForeground: "#010c1f",
    gridline: "#142a4080",
  },
  radii: {
    sm: "0.375rem",
    md: "0.625rem",
    lg: "0.875rem",
    xl: "1.25rem",
    full: "9999px",
  },
  spacing: {
    gutter: "1.5rem",
    container: "65rem",
  },
  shadows: {
    subtle: "0 1px 2px rgba(4, 16, 12, 0.25)",
    float: "0 8px 24px rgba(10, 22, 32, 0.35)",
    pop: "0 12px 32px rgba(15, 32, 48, 0.45)",
  },
  typography: {
    body: "'Inter Variable', 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    headings: "'Space Grotesk', 'Inter', system-ui, sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular",
  },
};

export const brandColorScale: ColorScale = {
  50: "#e7fbf4",
  100: "#c9f5e4",
  200: "#9debd0",
  300: "#6de1bb",
  400: "#3fd6a7",
  500: "#14c290",
  600: "#0fa67c",
  700: "#0b8864",
  800: "#076b4e",
  900: "#044936",
};

export const getToken = (path: keyof DesignTokens["colors"]): string => {
  return tradingAgentsTokens.colors[path];
};

export const tradingAgentsGradients = {
  sunrise: "linear-gradient(135deg, rgba(20,194,144,0.15), rgba(87,210,255,0.15))",
  depth: "linear-gradient(180deg, rgba(12,20,36,0.9), rgba(5,11,20,1))",
};
