import { useId, useRef } from 'react';
import { FilterX, MapPin, Search, X } from 'lucide-react';

import { Button, Select } from '@/components/ui';
import {
  ALL,
  AVAILABILITY_META,
  AVAILABILITY_ORDER,
  ORG_TYPES,
  ORG_TYPE_META,
  RESOURCE_FILTER_TYPES,
  hasActiveFilters,
} from '@/utils/networkDirectory';
import { RESOURCE_META } from '@/utils/theme';
import { cn } from '@/utils/cn';

/** Dropdown options, built once from the shared vocabularies. */
const RESOURCE_OPTIONS = [
  { value: ALL, label: 'All resource types' },
  ...RESOURCE_FILTER_TYPES.map((type) => ({ value: type, label: RESOURCE_META[type].label })),
];

const AVAILABILITY_OPTIONS = [
  { value: ALL, label: 'Any availability' },
  ...AVAILABILITY_ORDER.map((value) => ({ value, label: AVAILABILITY_META[value].label })),
];

/**
 * NetworkDirectoryFilters — the filter bar above the Network Directory.
 *
 *   Row 1  Organization-type chips: All · NGOs · Shelters · Rescue Partners ·
 *          Rescue Hubs, each with how many organizations it covers.
 *   Row 2  Search by name · Search by location.
 *   Row 3  Supported resource type · Availability (demo) · Clear Filters.
 *
 * Controlled: the page owns `filters` ({ name, location, category,
 * resourceType, availability }) and filters the directory itself, so every
 * change updates the cards and the map pins on the same render. `counts` is
 * `{ [categoryKey]: number }`, or null while the organizations are still
 * loading (the chips then show their label only).
 *
 * Availability is a DEMO value on invented organizations, not a live status —
 * the dropdown's label says so.
 *
 * Responsive: the two search boxes stack on mobile and sit side by side from
 * `sm` up. The two dropdowns stay side by side at every width (native
 * <select>s, so phones show their own picker) and Clear Filters spans the
 * row beneath them; from `lg` up all five controls share one row.
 *
 * Accessible: the type chips are a native radio group (arrow keys move
 * between them), the search boxes have visible labels and an Escape-to-clear
 * shortcut, and Clear Filters stays focusable when there is nothing to clear
 * so focus is never lost.
 */
export default function NetworkDirectoryFilters({ filters, counts, onChange, onClear }) {
  const groupName = useId();
  const { name, location, category, resourceType, availability } = filters;
  const canClear = hasActiveFilters(filters);

  const chips = [{ key: ALL, label: 'All' }, ...ORG_TYPES.map((type) => ({
    key: type,
    label: ORG_TYPE_META[type].label,
  }))];

  return (
    <div role="search" aria-label="Filter the network directory" className="mb-6 space-y-3">
      {/* ---------- Category chips ---------- */}
      <fieldset className="min-w-0">
        <legend className="sr-only">Organization type</legend>
        <div className="flex flex-wrap gap-2">
          {chips.map(({ key, label }) => {
            const checked = key === category;
            const count = counts?.[key];

            return (
              <label key={key} className="relative">
                <input
                  type="radio"
                  name={groupName}
                  value={key}
                  checked={checked}
                  onChange={() => onChange('category', key)}
                  className="peer sr-only"
                />
                <span
                  className={cn(
                    'inline-flex h-8 cursor-pointer select-none items-center gap-2 whitespace-nowrap rounded-control border px-3 text-[13px] font-medium tracking-tight',
                    'transition-colors duration-150',
                    'peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-400',
                    checked
                      ? 'border-brand-600 bg-brand-600 text-white'
                      : 'border-line bg-surface-2 text-muted hover:border-line-strong hover:bg-surface-3 hover:text-content',
                  )}
                >
                  {label}
                  {count !== undefined && (
                    <>
                      <span
                        aria-hidden="true"
                        className={cn(
                          'inline-flex h-4.5 min-w-4.5 items-center justify-center rounded-full px-1 text-[10px] font-semibold tabular',
                          checked ? 'bg-white/20 text-white' : 'bg-surface-3 text-faint',
                        )}
                      >
                        {count}
                      </span>
                      <span className="sr-only">({count})</span>
                    </>
                  )}
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {/* ---------- Search, dropdown filters, clear ---------- */}
      <div className="grid grid-cols-2 items-end gap-3 lg:grid-cols-[repeat(4,minmax(0,1fr))_auto]">
        <div className="col-span-2 sm:col-span-1">
          <SearchField
            label="Search by name"
            placeholder="Organization name..."
            icon={Search}
            value={name}
            onChange={(value) => onChange('name', value)}
          />
        </div>
        <div className="col-span-2 sm:col-span-1">
          <SearchField
            label="Search by location"
            placeholder="Area or city..."
            icon={MapPin}
            value={location}
            onChange={(value) => onChange('location', value)}
          />
        </div>

        <Select
          label="Supported resource type"
          value={resourceType}
          onChange={(event) => onChange('resourceType', event.target.value)}
          options={RESOURCE_OPTIONS}
        />
        <Select
          label="Availability (demo)"
          value={availability}
          onChange={(event) => onChange('availability', event.target.value)}
          options={AVAILABILITY_OPTIONS}
        />

        {/* aria-disabled (not disabled) so keyboard focus stays put after clearing. */}
        <Button
          variant="outline"
          icon={FilterX}
          onClick={canClear ? onClear : undefined}
          aria-disabled={canClear ? undefined : true}
          className={cn(
            'col-span-2 justify-center lg:col-span-1',
            !canClear && 'pointer-events-none opacity-60',
          )}
        >
          Clear Filters
        </Button>
      </div>
    </div>
  );
}

/** One labelled search box with an icon and a clear button. */
function SearchField({ label, placeholder, icon: Icon, value, onChange }) {
  const fieldId = useId();
  const inputRef = useRef(null);

  const clear = () => {
    onChange('');
    inputRef.current?.focus();
  };

  return (
    <div className="min-w-0">
      <label htmlFor={fieldId} className="mb-1.5 block text-xs font-medium tracking-wide text-muted">
        {label}
      </label>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint">
          <Icon size={15} strokeWidth={1.75} aria-hidden="true" />
        </span>
        <input
          id={fieldId}
          ref={inputRef}
          type="text"
          inputMode="search"
          autoComplete="off"
          spellCheck={false}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Escape' && value) {
              event.preventDefault();
              clear();
            }
          }}
          placeholder={placeholder}
          className="h-9.5 w-full rounded-control border border-line bg-surface-2 pl-9 pr-9 text-sm text-content transition-colors duration-150 placeholder:text-faint hover:border-line-strong focus:border-brand-500 focus:outline-none"
        />
        {value && (
          <button
            type="button"
            onClick={clear}
            aria-label={`Clear ${label.toLowerCase()}`}
            className="absolute right-1.5 top-1/2 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-faint transition-colors duration-150 hover:bg-surface-3 hover:text-content"
          >
            <X size={14} strokeWidth={2} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
