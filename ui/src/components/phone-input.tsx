"use client";

import { Input, Label, Select } from "@/components/ui";
import {
  DEFAULT_COUNTRY_CODE,
  PHONE_COUNTRY_CODES,
  sanitizeCountryCodeInput,
  sanitizeNationalNumberInput,
  type PhoneFields,
} from "@/lib/phone";

type PhoneInputProps = {
  label: string;
  countryCodeId: string;
  nationalNumberId: string;
  value: PhoneFields;
  onChange: (value: PhoneFields) => void;
  disabled?: boolean;
  required?: boolean;
  error?: string | null;
  hint?: string;
  hideLabel?: boolean;
};

export function PhoneInput({
  label,
  countryCodeId,
  nationalNumberId,
  value,
  onChange,
  disabled = false,
  required = false,
  error,
  hint,
  hideLabel = false,
}: PhoneInputProps) {
  const countryOptions = Array.from(
    new Set([DEFAULT_COUNTRY_CODE, ...PHONE_COUNTRY_CODES]),
  ).sort((a, b) => Number(a) - Number(b));

  return (
    <div>
      {hideLabel ? null : <Label>{label}</Label>}
      <div className={hideLabel ? "flex gap-2" : "mt-1.5 flex gap-2"}>
        <div className="w-24 shrink-0">
          <Label htmlFor={countryCodeId} className="sr-only">
            Country code
          </Label>
          <Select
            id={countryCodeId}
            aria-label="Country code"
            value={value.countryCode}
            disabled={disabled}
            required={required}
            onChange={(e) =>
              onChange({
                ...value,
                countryCode: sanitizeCountryCodeInput(e.target.value),
              })
            }
          >
            {countryOptions.map((code) => (
              <option key={code} value={code}>
                +{code}
              </option>
            ))}
          </Select>
        </div>
        <div className="min-w-0 flex-1">
          <Label htmlFor={nationalNumberId} className="sr-only">
            Phone number
          </Label>
          <Input
            id={nationalNumberId}
            inputMode="numeric"
            autoComplete="tel-national"
            placeholder="9876543210"
            value={value.nationalNumber}
            disabled={disabled}
            required={required}
            onChange={(e) =>
              onChange({
                ...value,
                nationalNumber: sanitizeNationalNumberInput(e.target.value),
              })
            }
          />
        </div>
      </div>
      {hint ? (
        <p className="mt-1.5 text-xs text-muted-foreground">{hint}</p>
      ) : null}
      {error ? <p className="mt-1.5 text-xs text-destructive">{error}</p> : null}
    </div>
  );
}
