export const getEnvVar = (key: string, fallback?: string): string => {
  if (typeof process === "undefined") {
    return fallback ?? "";
  }

  const value = process.env[key];
  if (value === undefined || value === "") {
    if (fallback !== undefined) {
      return fallback;
    }
    throw new Error(`Environment variable ${key} is not defined`);
  }

  return value;
};
