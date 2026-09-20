import { ChevronRight } from 'lucide-react';

import { StatusBadge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META } from '@/utils/theme';
import { formatQuantity, partnerCell, recipientCell } from '@/utils/operationFormat';
import { cn } from '@/utils/cn';

/**
 * OperationsTable — desktop view of the rescue operations list.
 *
 * Columns: Operation · Resource · Quantity · Provider · Recipient ·
 * Rescue Partner · Status · ETA · Deadline.
 *
 * Only shown from the `xl` breakpoint up (the page hides it below that and
 * renders OperationListCards instead). Free-text columns wrap; the ID and
 * status stay on one line.
 *
 * Every row is selectable: clicking anywhere on it, or pressing Enter/Space on
 * its ID button, calls `onSelect(operation)`. The row matching `selectedId` is
 * highlighted. Frontend only — the operations are mock data.
 */
export default function OperationsTable({ operations, selectedId, onSelect }) {
  return (
    <div className="panel overflow-x-auto">
      <table className="w-full border-collapse text-xs">
        <caption className="sr-only">
          Rescue operations (mock data). Select a row to open its details below.
        </caption>
        <thead>
          <tr className="bg-surface-2/60 text-left">
            <Th>Operation</Th>
            <Th>Resource</Th>
            <Th>Quantity</Th>
            <Th>Provider</Th>
            <Th>Recipient</Th>
            <Th>Rescue Partner</Th>
            <Th>Status</Th>
            <Th>ETA</Th>
            <Th>Deadline</Th>
            <Th>
              <span className="sr-only">Open details</span>
            </Th>
          </tr>
        </thead>
        <tbody>
          {operations.map((operation) => (
            <Row
              key={operation.id}
              operation={operation}
              selected={operation.id === selectedId}
              onSelect={onSelect}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Row({ operation, selected, onSelect }) {
  const { id, resource, resourceType, provider, status, eta, deadline } = operation;
  const Icon = RESOURCE_ICONS[resourceType];
  const typeLabel = RESOURCE_META[resourceType]?.label;
  const recipient = recipientCell(operation);
  const partner = partnerCell(operation);

  return (
    <tr
      onClick={() => onSelect(operation)}
      className={cn(
        'cursor-pointer border-t border-line align-top transition-colors duration-150',
        selected ? 'bg-veil-500/5' : 'hover:bg-surface-2/50',
      )}
    >
      <td
        className={cn(
          'whitespace-nowrap px-3 py-3.5',
          selected && 'shadow-[inset_2px_0_0_0_var(--color-veil-500)]',
        )}
      >
        {/* The row's click handler does the selecting; this button is the
            keyboard and screen-reader entry point (its click bubbles up). */}
        <button
          type="button"
          aria-label={`View details for ${id}`}
          aria-current={selected ? 'true' : undefined}
          className="rounded-sm font-mono text-xs font-medium text-content transition-colors duration-150 hover:text-veil-400"
        >
          {id}
        </button>
      </td>

      <td className="px-3 py-3.5">
        <div className="flex items-start gap-2">
          {Icon && (
            <span className="mt-0.5 shrink-0 text-veil-400">
              <Icon size={14} strokeWidth={1.75} />
            </span>
          )}
          <p className="min-w-0 font-medium text-content">
            {typeLabel && <span className="sr-only">{typeLabel}: </span>}
            {resource}
          </p>
        </div>
      </td>

      <td className="tabular whitespace-nowrap px-3 py-3.5 text-content">
        {formatQuantity(operation)}
      </td>

      <td className="px-3 py-3.5 text-content">{provider}</td>

      <td className={cn('px-3 py-3.5', recipient.empty ? 'text-faint' : 'text-content')}>
        {recipient.text}
      </td>

      <td className={cn('px-3 py-3.5', partner.empty ? 'text-faint' : 'text-content')}>
        {partner.text}
      </td>

      <td className="whitespace-nowrap px-3 py-3">
        <StatusBadge status={status} size="sm" />
      </td>

      <td className="px-3 py-3.5 text-content">{eta}</td>
      <td className="px-3 py-3.5 text-content">{deadline}</td>

      <td className="w-8 px-2 py-3.5 text-faint">
        <ChevronRight size={14} strokeWidth={1.75} aria-hidden="true" />
      </td>
    </tr>
  );
}

function Th({ children }) {
  return (
    <th
      scope="col"
      className="px-3 py-3 text-[11px] font-semibold uppercase tracking-wide text-faint"
    >
      {children}
    </th>
  );
}
