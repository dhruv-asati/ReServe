import { useId, useRef } from 'react';
import { FilterX, Search, X } from 'lucide-react';

import { Button, Select } from '@/components/ui';
import {
  QUICK_FILTERS,
  RESOURCE_TYPE_OPTIONS,
  STATUS_OPTIONS,
  hasActiveFilters,
} from '@/utils/operationFilters';
import { cn } from '@/utils/cn';

/**
 * OperationsFilters — the filter bar above the Operations list.
 *
 *   Row 1  Quick filters: All · Active · Completed · At Risk · Reallocating,
 *          each with how many operations of the full list it covers.
 *   Row 2  Search · Status · Resource Type · Clear Filters.
 *
 * Controlled: the page owns `filters` ({ query, quick, status, resourceType })
 * and filters the list itself, so every change updates the list on the same
 * render. `counts` is `{ [quickFilterKey]: number }`, or null while the
 * operations are still loading (the chips then show their label only).
 *
 * Responsive: below `xl` the search box has a row to itself. Under it the two
 * dropdowns sit side by side, and Clear Filters joins them from `sm` up (on
 * mobile it gets its own full-width row). From `xl` up it all fits in one row.
 *
 * Accessible: the quick filters are a native radio group (arrow keys move
 * between them, a screen reader announces "1 of 5"), every control has a
 * visible label, the search box explains what it covers, and Clear Filters
 * stays focusable when there is nothing to clear so focus is never lost.
 */
export default function OperationsFilters({ filters, counts, onChange, onClear }) {
  const searchId = useId();
  const hintId = useId();
  const groupName = useId();
  const searchRef = useRef(null);

  const { query, quick, status, resourceType } = filters;
  const canClear = hasActiveFilters(filters);

  const clearSearch = () => {
    onChange('query', '');
    searchRef.current?.focus();
  };

  return (
    <div role="search" aria-label="Filter operations" className="mb-4 space-y-3">
      {/* ---------- Quick filters ---------- */}
      <fieldset className="min-w-0">
        <legend className="sr-only">Quick filter</legend>
        <div className="flex flex-wrap gap-2">
          {QUICK_FILTERS.map(({ key, label }) => {
            const checked = key === quick;
            const count = counts?.[key];

            return (
              <label key={key} className="relative">
                <input
                  type="radio"
                  name={groupName}
                  value={key}
                  checked={checked}
                  onChange={() => onChange('quick', key)}
                  className="peer sr-only"
                />
                <span
                  className={cn(
                    'inline-flex h-8 cursor-pointer select-none items-center gap-2 whitespace-nowrap rounded-control border px-3 text-[13px] font-medium tracking-tight',
                    'transition-colors duration-150',
                    'peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-veil-400',
                    checked
                      ? 'border-veil-600 bg-veil-600 text-white'
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

      {/* ---------- Search + dropdowns ---------- */}
      <div className="grid grid-cols-2 items-end gap-3 sm:grid-cols-3 xl:grid-cols-[minmax(16rem,1fr)_12rem_10rem_auto]">
        <div className="col-span-2 sm:col-span-3 xl:col-span-1">
          <label
            htmlFor={searchId}
            className="mb-1.5 block text-xs font-medium tracking-wide text-muted"
          >
            Search
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint">
              <Search size={15} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <input
              id={searchId}
              ref={searchRef}
              type="text"
              inputMode="search"
              autoComplete="off"
              spellCheck={false}
              value={query}
              onChange={(event) => onChange('query', event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Escape' && query) {
                  event.preventDefault();
                  clearSearch();
                }
              }}
              placeholder="Search operations..."
              aria-describedby={hintId}
              className="h-9.5 w-full rounded-control border border-line bg-surface-2 pl-9 pr-9 text-sm text-content transition-colors duration-150 placeholder:text-faint hover:border-line-strong focus:border-veil-500 focus:outline-none"
            />
            {query && (
              <button
                type="button"
                onClick={clearSearch}
                aria-label="Clear search"
                className="absolute right-1.5 top-1/2 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-faint transition-colors duration-150 hover:bg-surface-3 hover:text-content"
              >
                <X size={14} strokeWidth={2} aria-hidden="true" />
              </button>
            )}
          </div>
        </div>

        <Select
          label="Status"
          value={status}
          onChange={(event) => onChange('status', event.target.value)}
          options={STATUS_OPTIONS}
        />

        <Select
          label="Resource Type"
          value={resourceType}
          onChange={(event) => onChange('resourceType', event.target.value)}
          options={RESOURCE_TYPE_OPTIONS}
        />

        {/* aria-disabled (not disabled) so keyboard focus stays put after clearing. */}
        <Button
          variant="outline"
          icon={FilterX}
          onClick={canClear ? onClear : undefined}
          aria-disabled={canClear ? undefined : true}
          className={cn(
            'col-span-2 justify-center sm:col-span-1',
            !canClear && 'pointer-events-none opacity-60',
          )}
        >
          Clear Filters
        </Button>
      </div>

      <p id={hintId} className="text-[11px] text-faint">
        Search covers operation ID, resource, provider, recipient, and rescue partner.
      </p>
    </div>
  );
}
