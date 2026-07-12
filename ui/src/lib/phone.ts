export const DEFAULT_COUNTRY_CODE = "91";

/** Common dial codes — longest codes should be matched first when splitting stored numbers. */
export const PHONE_COUNTRY_CODES = [
  "971",
  "966",
  "880",
  "977",
  "94",
  "92",
  "91",
  "86",
  "81",
  "65",
  "61",
  "49",
  "44",
  "33",
  "1",
] as const;

export type PhoneFields = {
  countryCode: string;
  nationalNumber: string;
};

export const EMPTY_PHONE_FIELDS: PhoneFields = {
  countryCode: DEFAULT_COUNTRY_CODE,
  nationalNumber: "",
};

export function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

export function splitStoredPhone(stored: string | null | undefined): PhoneFields {
  const digits = digitsOnly(stored ?? "");
  if (!digits) {
    return { ...EMPTY_PHONE_FIELDS };
  }

  const sortedCodes = [...PHONE_COUNTRY_CODES].sort(
    (a, b) => b.length - a.length,
  );
  for (const code of sortedCodes) {
    if (digits.startsWith(code) && digits.length > code.length + 5) {
      return {
        countryCode: code,
        nationalNumber: digits.slice(code.length),
      };
    }
  }

  return {
    countryCode: DEFAULT_COUNTRY_CODE,
    nationalNumber: digits,
  };
}

export function combinePhoneParts(fields: PhoneFields): string {
  const countryCode = digitsOnly(fields.countryCode);
  const nationalNumber = digitsOnly(fields.nationalNumber);

  if (!countryCode) {
    throw new Error("Country code is required.");
  }
  if (countryCode.length < 1 || countryCode.length > 3) {
    throw new Error("Country code must be 1–3 digits.");
  }
  if (!nationalNumber) {
    throw new Error("Phone number is required.");
  }
  if (nationalNumber.length < 6 || nationalNumber.length > 12) {
    throw new Error("Phone number must be 6–12 digits without country code.");
  }

  const full = `${countryCode}${nationalNumber}`;
  if (full.length < 8 || full.length > 15) {
    throw new Error("Full phone number must be 8–15 digits including country code.");
  }
  return full;
}

export function combineOptionalPhoneParts(
  fields: PhoneFields,
): string | null {
  const nationalNumber = digitsOnly(fields.nationalNumber);
  if (!nationalNumber) {
    return null;
  }
  return combinePhoneParts(fields);
}

export function formatPhoneDisplay(stored: string | null | undefined): string {
  const digits = digitsOnly(stored ?? "");
  if (!digits) return "—";
  const { countryCode, nationalNumber } = splitStoredPhone(digits);
  return `${countryCode} ${nationalNumber}`;
}

export function sanitizeCountryCodeInput(value: string): string {
  return digitsOnly(value).slice(0, 3);
}

export function sanitizeNationalNumberInput(value: string): string {
  return digitsOnly(value).slice(0, 12);
}
