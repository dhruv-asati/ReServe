import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Tag,
  Hash,
  Scale,
  Clock,
  CalendarClock,
  MapPin,
  FileText,
  Barcode,
  PlusCircle,
} from 'lucide-react';

import { Card, Button, Input, Select, Textarea } from '@/components/ui';
import ResourceTypeCard from '@/components/create-rescue/ResourceTypeCard';
import FileUploadField from '@/components/create-rescue/FileUploadField';
import RescueSummaryPanel from '@/components/create-rescue/RescueSummaryPanel';
import { RESOURCE_TYPE } from '@/utils/theme';
import { RESOURCE_ICONS } from '@/utils/icons';
import { CATEGORY_OPTIONS, UNIT_OPTIONS, PREPARATION_TIME_OPTIONS } from '@/data/rescueForm';
import { createRescue } from '@/services/rescueService';
import { PATHS, toPath } from '@/routes/paths';

/** Fields every resource type shares. */
const BASE_FIELDS = { category: '', quantity: '', unit: '', location: '', description: '' };

/** Fields specific to Food. */
const FOOD_FIELDS = { preparationTime: '', pickupDeadline: '' };

/** Fields specific to Medical Resources. */
const MEDICAL_FIELDS = { resourceName: '', expiry: '', batchReference: '' };

function initialForm() {
  return { resourceType: '', ...BASE_FIELDS, ...FOOD_FIELDS, ...MEDICAL_FIELDS };
}

/**
 * Validate the form for the currently selected resource type. Only fields
 * relevant to that type are checked — the other type's fields are ignored
 * even if left over in state from a prior selection. Uploads are optional,
 * so they are never part of validation.
 */
function validate(form) {
  const errors = {};

  if (!form.resourceType) {
    errors.resourceType = 'Select a resource type to continue.';
    return errors; // Nothing else can be validated meaningfully yet.
  }

  if (!form.category) errors.category = 'Category is required.';

  if (!form.quantity.toString().trim()) {
    errors.quantity = 'Quantity is required.';
  } else if (Number(form.quantity) <= 0) {
    errors.quantity = 'Quantity must be greater than 0.';
  }

  if (!form.unit) errors.unit = 'Unit is required.';
  if (!form.location.trim()) errors.location = 'Pickup location is required.';

  if (form.resourceType === RESOURCE_TYPE.FOOD) {
    if (!form.preparationTime) errors.preparationTime = 'Preparation time is required.';
    if (!form.pickupDeadline) errors.pickupDeadline = 'Pickup deadline is required.';
  }

  if (form.resourceType === RESOURCE_TYPE.MEDICAL) {
    if (!form.resourceName.trim()) errors.resourceName = 'Resource name is required.';
    if (!form.expiry) errors.expiry = 'Expiry date is required.';
  }

  return errors;
}

/** Strip in-memory File objects down to plain, serializable metadata. */
function toFileMetadata(uploadItems) {
  return uploadItems.map(({ file }) => ({
    name: file.name,
    size: file.size,
    type: file.type,
  }));
}

/**
 * CreateRescue — base rescue creation form.
 *
 * Frontend only: submission goes through services/rescueService (mock),
 * same pattern as every other service in the app. Uploaded images/documents
 * never leave the browser — they're held as in-memory File objects for
 * preview and reduced to {name, size, type} metadata before anything is
 * persisted. On a successful mock submit the resource is saved to
 * localStorage and the person is taken to the mock AI analysis stage; the
 * analysis itself is a separate, later step and is not implemented here.
 */
export default function CreateRescue() {
  const navigate = useNavigate();

  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [imageFiles, setImageFiles] = useState([]);
  const [documentFiles, setDocumentFiles] = useState([]);

  const categoryOptions = form.resourceType ? CATEGORY_OPTIONS[form.resourceType] : [];
  const unitOptions = form.resourceType ? UNIT_OPTIONS[form.resourceType] : [];

  function updateField(field, value) {
    const next = { ...form, [field]: value };
    setForm(next);
    if (touched[field]) {
      setErrors(validate(next));
    }
  }

  function handleBlur(field) {
    setTouched((prev) => ({ ...prev, [field]: true }));
    setErrors(validate(form));
  }

  function selectResourceType(type) {
    // Switching type clears the other type's fields and uploads so nothing
    // stray can be submitted for the wrong resource type.
    setForm({ resourceType: type, ...BASE_FIELDS, ...FOOD_FIELDS, ...MEDICAL_FIELDS });
    setErrors({});
    setTouched({});
    setFormError('');
    setImageFiles([]);
    setDocumentFiles([]);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');

    const nextErrors = validate(form);
    setErrors(nextErrors);
    setTouched({
      resourceType: true,
      category: true,
      quantity: true,
      unit: true,
      location: true,
      ...(form.resourceType === RESOURCE_TYPE.FOOD && {
        preparationTime: true,
        pickupDeadline: true,
      }),
      ...(form.resourceType === RESOURCE_TYPE.MEDICAL && {
        resourceName: true,
        expiry: true,
      }),
    });

    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      const payload = {
        ...form,
        images: form.resourceType === RESOURCE_TYPE.FOOD ? toFileMetadata(imageFiles) : undefined,
        documents:
          form.resourceType === RESOURCE_TYPE.MEDICAL ? toFileMetadata(documentFiles) : undefined,
      };
      const result = await createRescue(payload);
      // Mock AI analysis is a later step — this only navigates to its slot.
      navigate(toPath(PATHS.RESOURCE_DETAILS, { rescueId: result.id }), {
        state: { justCreated: true, resourceId: result.id },
      });
    } catch (err) {
      setSubmitting(false);
      setFormError(err?.message ?? 'Something went wrong creating this rescue. Please try again.');
    }
  }

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      <div>
        <Link
          to={PATHS.DASHBOARD}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted transition-colors hover:text-content"
        >
          <ArrowLeft size={13} strokeWidth={1.75} />
          Back to dashboard
        </Link>
        <h1 className="mt-2 text-xl font-bold tracking-tight text-content sm:text-2xl">
          Create Rescue
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          Log a surplus resource so it can be matched and rescued before it&rsquo;s lost.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-6 lg:space-y-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start lg:gap-8">
          {/* ---------- Left: form fields ---------- */}
          <div className="min-w-0 space-y-6 lg:space-y-8">
            {/* ---------- Resource type ---------- */}
            <Card>
              <Card.Header
                title="Resource type"
                subtitle="Choose what kind of surplus you're logging — the form below adapts to it."
              />
              <Card.Body>
                <div
                  role="radiogroup"
                  aria-label="Resource type"
                  aria-required="true"
                  className="grid grid-cols-1 gap-3 sm:grid-cols-2"
                >
                  <ResourceTypeCard
                    name="resourceType"
                    value={RESOURCE_TYPE.FOOD}
                    label="Food"
                    description="Prepared meals, produce, bakery, and other perishable or packaged food surplus."
                    icon={RESOURCE_ICONS.food}
                    tone="food"
                    checked={form.resourceType === RESOURCE_TYPE.FOOD}
                    onChange={selectResourceType}
                  />
                  <ResourceTypeCard
                    name="resourceType"
                    value={RESOURCE_TYPE.MEDICAL}
                    label="Medical Resources"
                    description="Medications, vaccines, PPE, and other medical supplies for coordination only."
                    icon={RESOURCE_ICONS.medical}
                    tone="medical"
                    checked={form.resourceType === RESOURCE_TYPE.MEDICAL}
                    onChange={selectResourceType}
                  />
                </div>
                {touched.resourceType && errors.resourceType && (
                  <p className="mt-3 text-xs text-critical">{errors.resourceType}</p>
                )}
              </Card.Body>
            </Card>

            {/* ---------- Resource details (adapts to resourceType) ---------- */}
            {form.resourceType && (
              <Card>
                <Card.Header
                  title="Resource details"
                  subtitle={
                    form.resourceType === RESOURCE_TYPE.FOOD
                      ? 'Tell us what food is available and when it needs to be picked up.'
                      : 'Tell us what medical resource is available and its expiry.'
                  }
                />
                <Card.Body className="space-y-5">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <Select
                      label="Category"
                      required
                      icon={Tag}
                      placeholder="Select a category"
                      options={categoryOptions}
                      value={form.category}
                      onChange={(e) => updateField('category', e.target.value)}
                      onBlur={() => handleBlur('category')}
                      error={touched.category ? errors.category : undefined}
                    />

                    {form.resourceType === RESOURCE_TYPE.MEDICAL && (
                      <Input
                        label="Resource name"
                        required
                        icon={Tag}
                        placeholder="e.g. Amoxicillin 500mg"
                        value={form.resourceName}
                        onChange={(e) => updateField('resourceName', e.target.value)}
                        onBlur={() => handleBlur('resourceName')}
                        error={touched.resourceName ? errors.resourceName : undefined}
                      />
                    )}

                    <Input
                      label="Quantity"
                      required
                      type="number"
                      min="0"
                      step="any"
                      icon={Hash}
                      placeholder="e.g. 50"
                      value={form.quantity}
                      onChange={(e) => updateField('quantity', e.target.value)}
                      onBlur={() => handleBlur('quantity')}
                      error={touched.quantity ? errors.quantity : undefined}
                    />

                    <Select
                      label="Unit"
                      required
                      icon={Scale}
                      placeholder="Select a unit"
                      options={unitOptions}
                      value={form.unit}
                      onChange={(e) => updateField('unit', e.target.value)}
                      onBlur={() => handleBlur('unit')}
                      error={touched.unit ? errors.unit : undefined}
                    />

                    {form.resourceType === RESOURCE_TYPE.FOOD && (
                      <>
                        <Select
                          label="Preparation time"
                          required
                          icon={Clock}
                          placeholder="How soon is it ready?"
                          options={PREPARATION_TIME_OPTIONS}
                          value={form.preparationTime}
                          onChange={(e) => updateField('preparationTime', e.target.value)}
                          onBlur={() => handleBlur('preparationTime')}
                          error={touched.preparationTime ? errors.preparationTime : undefined}
                        />

                        <Input
                          label="Pickup deadline"
                          required
                          type="datetime-local"
                          icon={CalendarClock}
                          value={form.pickupDeadline}
                          onChange={(e) => updateField('pickupDeadline', e.target.value)}
                          onBlur={() => handleBlur('pickupDeadline')}
                          error={touched.pickupDeadline ? errors.pickupDeadline : undefined}
                        />
                      </>
                    )}

                    {form.resourceType === RESOURCE_TYPE.MEDICAL && (
                      <>
                        <Input
                          label="Expiry"
                          required
                          type="date"
                          icon={CalendarClock}
                          value={form.expiry}
                          onChange={(e) => updateField('expiry', e.target.value)}
                          onBlur={() => handleBlur('expiry')}
                          error={touched.expiry ? errors.expiry : undefined}
                        />

                        <Input
                          label="Batch / reference"
                          icon={Barcode}
                          placeholder="e.g. LOT-2291 (if available)"
                          hint="Optional — include if the batch or lot number is known."
                          value={form.batchReference}
                          onChange={(e) => updateField('batchReference', e.target.value)}
                        />
                      </>
                    )}

                    <Input
                      label="Location"
                      required
                      icon={MapPin}
                      placeholder="Pickup address or site name"
                      containerClassName="sm:col-span-2"
                      value={form.location}
                      onChange={(e) => updateField('location', e.target.value)}
                      onBlur={() => handleBlur('location')}
                      error={touched.location ? errors.location : undefined}
                    />
                  </div>

                  <Textarea
                    label="Description"
                    icon={FileText}
                    rows={3}
                    placeholder="Any extra detail that helps a partner assess and pick this up…"
                    hint="Optional — packaging, handling notes, allergens, storage needs."
                    value={form.description}
                    onChange={(e) => updateField('description', e.target.value)}
                  />

                  {form.resourceType === RESOURCE_TYPE.FOOD && (
                    <FileUploadField
                      label="Photos"
                      hint="Optional — a photo helps partners assess condition and quantity at a glance."
                      accept="image/*"
                      preview="thumbnail"
                      emptyLabel="Click to upload photos or drag and drop"
                      files={imageFiles}
                      onFilesChange={setImageFiles}
                    />
                  )}

                  {form.resourceType === RESOURCE_TYPE.MEDICAL && (
                    <FileUploadField
                      label="Supporting documents"
                      hint="Optional — spec sheets, donation letters, or cold-chain records."
                      accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
                      preview="list"
                      emptyLabel="Click to upload documents or drag and drop"
                      files={documentFiles}
                      onFilesChange={setDocumentFiles}
                    />
                  )}
                </Card.Body>
              </Card>
            )}
          </div>

          {/* ---------- Right: live summary ---------- */}
          <RescueSummaryPanel form={form} imageFiles={imageFiles} documentFiles={documentFiles} />
        </div>

        {formError && (
          <p className="rounded-control border border-critical/30 bg-critical/10 px-3 py-2 text-xs text-critical">
            {formError}
          </p>
        )}

        {/* ---------- Actions ---------- */}
        <div className="flex flex-col-reverse items-stretch justify-end gap-2.5 sm:flex-row sm:items-center">
          <Button
            type="button"
            variant="secondary"
            disabled={submitting}
            onClick={() => navigate(PATHS.DASHBOARD)}
            className="justify-center"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={submitting}
            icon={submitting ? undefined : PlusCircle}
            className="justify-center"
          >
            {submitting ? 'Submitting…' : 'Create Rescue'}
          </Button>
        </div>
      </form>
    </div>
  );
}
