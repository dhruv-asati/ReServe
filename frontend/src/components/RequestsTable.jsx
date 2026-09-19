import { ArrowRight, Eye } from 'lucide-react';

import { Badge, Button, StatusBadge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META } from '@/utils/theme';

/**
 * RequestsTable — desktop view of the Rescue Requests page.
 *
 * Columns: Request · Resource · Quantity · Provider / Recipient · Location ·
 * Deadline · Status · Action.
 *
 * Only shown from the `xl` breakpoint up (the page hides it below that and
 * renders RequestCards instead), so it never has to scroll horizontally.
 * Free-text columns wrap; ID, status and action stay on one line.
 */
export default function RequestsTable({ requests, onViewDetails }) {
  return (
    <div className="panel overflow-hidden">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Rescue requests</caption>
        <thead>
          <tr className="bg-surface-2/60 text-left">
            <Th>Request</Th>
            <Th>Resource</Th>
            <Th>Quantity</Th>
            <Th>Provider / Recipient</Th>
            <Th>Location</Th>
            <Th>Deadline</Th>
            <Th>Status</Th>
            <Th className="text-right">Action</Th>
          </tr>
        </thead>
        <tbody>
          {requests.map((request) => (
            <Row key={request.id} request={request} onViewDetails={onViewDetails} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Row({ request, onViewDetails }) {
  const { id, resource, resourceType, quantity, provider, recipient, location, deadline, status } =
    request;
  const Icon = RESOURCE_ICONS[resourceType];
  const typeMeta = RESOURCE_META[resourceType];

  return (
    <tr className="border-t border-line align-top transition-colors duration-150 hover:bg-surface-2/50">
      <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs font-medium text-content">
        {id}
      </td>

      <td className="px-4 py-3.5">
        <div className="flex items-start gap-2">
          {Icon && (
            <span className="mt-0.5 shrink-0 text-brand-400">
              <Icon size={15} strokeWidth={1.75} />
            </span>
          )}
          <div className="min-w-0">
            <p className="font-medium text-content">{resource}</p>
            <Badge tone={typeMeta ? resourceType : 'neutral'} size="sm" className="mt-1">
              {typeMeta?.label ?? resourceType}
            </Badge>
          </div>
        </div>
      </td>

      <td className="tabular px-4 py-3.5 text-content">{quantity}</td>

      <td className="px-4 py-3.5">
        <p className="font-medium text-content">{provider}</p>
        <p className="mt-0.5 flex items-start gap-1 text-xs text-muted">
          <ArrowRight size={12} strokeWidth={2} className="mt-0.5 shrink-0" aria-label="to" />
          <span>{recipient}</span>
        </p>
      </td>

      <td className="px-4 py-3.5 text-muted">{location}</td>
      <td className="px-4 py-3.5 text-content">{deadline}</td>

      <td className="whitespace-nowrap px-4 py-3.5">
        <StatusBadge status={status} size="sm" />
      </td>

      <td className="whitespace-nowrap px-4 py-3 text-right">
        <Button
          variant="outline"
          size="sm"
          icon={Eye}
          onClick={() => onViewDetails?.(request)}
          aria-label={`View details for ${id}`}
        >
          View Details
        </Button>
      </td>
    </tr>
  );
}

function Th({ className = '', children }) {
  return (
    <th
      scope="col"
      className={`px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-faint ${className}`}
    >
      {children}
    </th>
  );
}
