const DEFAULT_LOCALE = "en-US";

export const formatCurrency = (
  value: number,
  currency: string = "USD",
  locale: string = DEFAULT_LOCALE,
): string =>
  Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);

export const formatPercent = (
  value: number,
  locale: string = DEFAULT_LOCALE,
  options: Pick<Intl.NumberFormatOptions, "maximumFractionDigits"> = {
    maximumFractionDigits: 2,
  },
): string =>
  Intl.NumberFormat(locale, {
    style: "percent",
    maximumFractionDigits: options.maximumFractionDigits,
  }).format(value);

export const formatDate = (
  input: string | Date,
  locale: string = DEFAULT_LOCALE,
  options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
  },
): string =>
  Intl.DateTimeFormat(locale, options).format(
    typeof input === "string" ? new Date(input) : input,
  );
