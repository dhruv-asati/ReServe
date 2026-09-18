import { FileText, MapPin, Package } from 'lucide-react';

import { Card, Badge } from '@/components/ui';
import { RESOURCE_TYPE } from '@/utils/theme';
import { RESOURCE_ICONS } from '@/utils/icons';
import { CATEGORY_OPTIONS, UNIT_OPTIONS, PREPARATION_TIME_OPTIONS } from '@/data/rescueForm';

/** Look up a display label for a value from an {value,label} option list. */
function labelFor(options, value) {
  return options.find((opt) => opt.value === value)?.label;
}

function SummaryRow({ label, value, placeholder = 'Not provided yet' }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2 text-xs">
      <span className="shrink-0 text-faint">{label}</span>
      <span className={value ? 'text-right font-medium text-content' : 'text-right text-faint italic'}>
        {value || placeholder}
      </span>
    </div>
  );
}

/**
 * RescueSummaryPanel — read-only recap of the form so far, kept in sync
 * live as the person fills it in. Purely presentational: it derives every
 * line from `form`/`files` and writes nothing back.
 */
export default function RescueSummaryPanel({ form, imageFiles = [], documentFiles = [] }) {
  const { resourceType } = form;
  const TypeIcon = resourceType ? RESOURCE_ICONS[resourceType] : Package;

  const categoryLabel = resourceType ? labelFor(CATEGORY_OPTIONS[resourceType], form.category) : null;
  const unitLabel = resourceType ? labelFor(UNIT_OPTIONS[resourceType], form.unit) : null;
  const prepLabel =
    resourceType === RESOURCE_TYPE.FOOD
      ? labelFor(PREPARATION_TIME_OPTIONS, form.preparationTime)
      : null;

  const quantityValue = form.quantity && unitLabel ? `${form.quantity} ${unitLabel}` : form.quantity || '';

  return (
    <Card className="lg:sticky lg:top-6">
      <Card.Header
        icon={FileText}
        title="Rescue Summary"
        subtitle="What will be submitted, reviewed live as you fill in the form."
      />
      <Card.Body className="space-y-1 divide-y divide-line">
        <div className="flex items-center justify-between pb-2">
          <span className="text-xs text-faint">Resource type</span>
          {resourceType ? (
            <Badge tone={resourceType} icon={TypeIcon} size="sm">
              {resourceType === RESOURCE_TYPE.FOOD ? 'Food' : 'Medical Resources'}
            </Badge>
          ) : (
            <span className="text-xs italic text-faint">Not selected yet</span>
          )}
        </div>

        <SummaryRow label="Category" value={categoryLabel} />

        {resourceType === RESOURCE_TYPE.MEDICAL && (
          <SummaryRow label="Resource name" value={form.resourceName} />
        )}

        <SummaryRow label="Quantity" value={quantityValue} />

        {resourceType === RESOURCE_TYPE.FOOD && (
          <>
            <SummaryRow label="Preparation time" value={prepLabel} />
            <SummaryRow
              label="Pickup deadline"
              value={form.pickupDeadline && new Date(form.pickupDeadline).toLocaleString()}
            />
          </>
        )}

        {resourceType === RESOURCE_TYPE.MEDICAL && (
          <>
            <SummaryRow
              label="Expiry"
              value={form.expiry && new Date(form.expiry).toLocaleDateString()}
            />
            <SummaryRow label="Batch / reference" value={form.batchReference} placeholder="Not provided" />
          </>
        )}

        <SummaryRow label="Location" value={form.location} />

        <div className="py-2">
          <span className="mb-1 flex items-center gap-1.5 text-xs text-faint">
            <MapPin size={12} strokeWidth={1.75} className="shrink-0" />
            Description
          </span>
          <p className={form.description ? 'text-xs text-content' : 'text-xs italic text-faint'}>
            {form.description || 'Not provided yet'}
          </p>
        </div>

        {resourceType === RESOURCE_TYPE.FOOD && (
          <SummaryRow
            label="Photos attached"
            value={imageFiles.length > 0 ? `${imageFiles.length} image${imageFiles.length > 1 ? 's' : ''}` : ''}
            placeholder="None attached"
          />
        )}

        {resourceType === RESOURCE_TYPE.MEDICAL && (
          <SummaryRow
            label="Documents attached"
            value={
              documentFiles.length > 0
                ? `${documentFiles.length} file${documentFiles.length > 1 ? 's' : ''}`
                : ''
            }
            placeholder="None attached"
          />
        )}
      </Card.Body>
    </Card>
  );
}
