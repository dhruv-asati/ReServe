import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock,
  Mail,
  MapPin,
  MinusCircle,
  PackageCheck,
  Pencil,
  Phone,
  RotateCcw,
  Save,
  ShieldCheck,
} from 'lucide-react';

import { Badge, Button, Card, ErrorState, Input, LoadingState, Select, Textarea } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { buildDefaultProfile } from '@/data/profile';
import { getOrganizationProfile, updateOrganizationProfile } from '@/services/profileService';
import { cn } from '@/utils/cn';
import { RESOURCE_ICONS } from '@/utils/icons';
import {
  DAYS,
  ORG_TYPE_LABELS,
  ORG_TYPE_OPTIONS,
  hasErrors,
  initialsFromName,
  summarizeOperatingHours,
  validateProfile,
} from '@/utils/profile';
import { RESOURCE_META, RESOURCE_TYPE } from '@/utils/theme';
import { VERIFICATION_META } from '@/utils/networkDirectory';

/** Icon for each verification value — mirrors the yes/no/unknown vocabulary StatusCheckBadge uses. */
const VERIFICATION_ICONS = {
  verified: CheckCircle2,
  pending: Clock,
  unlisted: MinusCircle,
};

/**
 * Organization Profile (`/app/profile`).
 *
 * Replaces the earlier placeholder with a working profile: an operator's
 * organization details, contact info, service area and hours, supported
 * resource types, capacity and requirements, and a (read-only) verification
 * status — editable in place with validation and save/cancel.
 *
 * There is no backend behind this page yet. `data/profile.js` seeds a
 * starter profile from the signed-in account (see services/auth.js), and
 * `services/profileService.js` persists edits to localStorage keyed by that
 * account's email — the same mock-request + localStorage pattern the rest
 * of the app uses (see services/auth.js, services/profileService.js). The
 * page therefore works fully with the backend OFF, and edits survive a
 * refresh for that account.
 */
export default function Profile() {
  const { user } = useAuth();

  const [profile, setProfile] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(null);
  const [errors, setErrors] = useState({});

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [justSaved, setJustSaved] = useState(false);

  const load = useCallback(() => {
    let active = true;
    setProfile(null);
    setLoadError(null);

    getOrganizationProfile(user?.email, buildDefaultProfile(user))
      .then((data) => {
        if (active) setProfile(data);
      })
      .catch((err) => {
        if (active) setLoadError(err);
      });

    return () => {
      active = false;
    };
  }, [user]);

  useEffect(() => load(), [load]);

  // Auto-dismiss the "saved" confirmation so it doesn't linger indefinitely.
  useEffect(() => {
    if (!justSaved) return undefined;
    const timer = setTimeout(() => setJustSaved(false), 4000);
    return () => clearTimeout(timer);
  }, [justSaved]);

  const startEditing = () => {
    setDraft(structuredClone(profile));
    setErrors({});
    setSaveError(null);
    setJustSaved(false);
    setEditing(true);
  };

  const cancelEditing = () => {
    setDraft(null);
    setErrors({});
    setSaveError(null);
    setEditing(false);
  };

  const updateField = (key, value) => setDraft((d) => ({ ...d, [key]: value }));

  const updateCapacity = (key, value) =>
    setDraft((d) => ({ ...d, capacity: { ...d.capacity, [key]: value } }));

  const toggleResourceType = (type) =>
    setDraft((d) => {
      const has = d.resourceTypes.includes(type);
      const resourceTypes = has
        ? d.resourceTypes.filter((t) => t !== type)
        : [...d.resourceTypes, type];
      return { ...d, resourceTypes };
    });

  const updateHoursRow = (index, patch) =>
    setDraft((d) => ({
      ...d,
      operatingHours: d.operatingHours.map((row, i) => (i === index ? { ...row, ...patch } : row)),
    }));

  const handleSave = async (event) => {
    event.preventDefault();
    if (!editing || !draft) return;

    const validationErrors = validateProfile(draft);
    setErrors(validationErrors);
    if (hasErrors(validationErrors)) return;

    setSaving(true);
    setSaveError(null);
    try {
      const saved = await updateOrganizationProfile(user?.email, draft);
      setProfile(saved);
      setDraft(null);
      setEditing(false);
      setJustSaved(true);
    } catch (err) {
      setSaveError(err?.message ?? 'Could not save your changes. Try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!profile) {
    return (
      <div className="animate-fade-up space-y-6 lg:space-y-8">
        <PageHeader />
        {loadError ? (
          <div className="panel">
            <ErrorState
              title="Couldn't load your profile"
              description={loadError?.message ?? 'Something went wrong loading your organization profile.'}
              onRetry={load}
            />
          </div>
        ) : (
          <LoadingState variant="skeleton" rows={4} label="Loading your organization profile…" />
        )}
      </div>
    );
  }

  const verificationMeta = VERIFICATION_META[profile.verification];
  const VerificationIcon = VERIFICATION_ICONS[profile.verification] ?? MinusCircle;

  return (
    <form className="animate-fade-up space-y-6 lg:space-y-8" onSubmit={handleSave} noValidate>
      <PageHeader />

      {justSaved && (
        <div
          role="status"
          className="flex items-start gap-2.5 rounded-control border border-success/25 bg-success/10 px-3.5 py-2.5 text-sm font-medium text-success"
        >
          <CheckCircle2 size={16} strokeWidth={2} className="mt-0.5 shrink-0" />
          Profile updated successfully.
        </div>
      )}
      {saveError && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-control border border-critical/25 bg-critical/10 px-3.5 py-2.5 text-sm font-medium text-critical"
        >
          <AlertTriangle size={16} strokeWidth={2} className="mt-0.5 shrink-0" />
          {saveError}
        </div>
      )}

      {/* ---------- Identity + actions ---------- */}
      <Card>
        <Card.Body className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-start gap-4">
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-control bg-brand-500/15 text-lg font-semibold tracking-tight text-brand-400 ring-1 ring-inset ring-brand-500/25">
              {initialsFromName(profile.organizationName)}
            </span>

            <div className="min-w-0 pt-0.5">
              {editing ? (
                <Input
                  label="Organization name"
                  required
                  value={draft.organizationName}
                  onChange={(e) => updateField('organizationName', e.target.value)}
                  error={errors.organizationName}
                  containerClassName="max-w-xs"
                />
              ) : (
                <h1 className="truncate text-xl font-bold tracking-tight text-content sm:text-2xl">
                  {profile.organizationName}
                </h1>
              )}

              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Badge tone="brand">{ORG_TYPE_LABELS[profile.type] ?? profile.type}</Badge>
                {verificationMeta && (
                  <Badge tone={verificationMeta.tone} icon={VerificationIcon}>
                    {verificationMeta.label}
                  </Badge>
                )}
              </div>
            </div>
          </div>

          <div className="flex shrink-0 gap-2">
            {editing ? (
              <>
                <Button type="button" variant="secondary" icon={RotateCcw} onClick={cancelEditing} disabled={saving}>
                  Cancel
                </Button>
                <Button type="submit" icon={Save} loading={saving}>
                  Save Changes
                </Button>
              </>
            ) : (
              <Button type="button" icon={Pencil} onClick={startEditing}>
                Edit Profile
              </Button>
            )}
          </div>
        </Card.Body>
      </Card>

      {/* ---------- Main grid ---------- */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
        <div className="space-y-6 lg:col-span-2 lg:space-y-8">
          {/* Contact details */}
          <Card>
            <Card.Header
              icon={Building2}
              title="Contact Details"
              subtitle="Organization type and how partners can reach you"
            />
            <Card.Body className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {editing ? (
                <>
                  <Select
                    label="Organization type"
                    required
                    options={ORG_TYPE_OPTIONS}
                    value={draft.type}
                    onChange={(e) => updateField('type', e.target.value)}
                    error={errors.type}
                  />
                  <Input
                    label="Contact name"
                    value={draft.contactName}
                    onChange={(e) => updateField('contactName', e.target.value)}
                    hint="Optional"
                  />
                  <Input
                    label="Email"
                    type="email"
                    required
                    icon={Mail}
                    value={draft.email}
                    onChange={(e) => updateField('email', e.target.value)}
                    error={errors.email}
                  />
                  <Input
                    label="Phone"
                    type="tel"
                    icon={Phone}
                    value={draft.phone}
                    onChange={(e) => updateField('phone', e.target.value)}
                    error={errors.phone}
                    hint={errors.phone ? undefined : 'Optional'}
                  />
                  <Textarea
                    label="Address"
                    required
                    rows={2}
                    containerClassName="sm:col-span-2"
                    value={draft.address}
                    onChange={(e) => updateField('address', e.target.value)}
                    error={errors.address}
                  />
                </>
              ) : (
                <>
                  <ProfileField label="Organization type" value={ORG_TYPE_LABELS[profile.type] ?? profile.type} />
                  <ProfileField label="Contact name" value={profile.contactName || '—'} />
                  <ProfileField icon={Mail} label="Email" value={profile.email || '—'} />
                  <ProfileField icon={Phone} label="Phone" value={profile.phone || '—'} />
                  <ProfileField
                    icon={MapPin}
                    label="Address"
                    value={profile.address || '—'}
                    className="sm:col-span-2"
                  />
                </>
              )}
            </Card.Body>
          </Card>

          {/* Service area + operating hours */}
          <Card>
            <Card.Header
              icon={Clock}
              title="Service Area & Operating Hours"
              subtitle="Where you operate and when you're reachable"
            />
            <Card.Body className="space-y-5">
              {editing ? (
                <Input
                  label="Service area"
                  required
                  icon={MapPin}
                  value={draft.serviceArea}
                  onChange={(e) => updateField('serviceArea', e.target.value)}
                  error={errors.serviceArea}
                />
              ) : (
                <ProfileField icon={MapPin} label="Service area" value={profile.serviceArea || '—'} />
              )}

              <div>
                <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-faint">
                  Operating hours
                </p>

                {editing ? (
                  <div className="space-y-2">
                    {errors.operatingHours && (
                      <p className="text-xs text-critical">{errors.operatingHours}</p>
                    )}
                    {draft.operatingHours.map((row, index) => {
                      const day = DAYS.find((d) => d.key === row.day);
                      return (
                        <div
                          key={row.day}
                          className="flex flex-wrap items-center gap-3 rounded-control border border-line bg-surface-2 px-3 py-2"
                        >
                          <span className="w-9 shrink-0 text-xs font-medium text-content">
                            {day?.short ?? row.day}
                          </span>
                          <label className="flex shrink-0 items-center gap-1.5 text-xs text-muted">
                            <input
                              type="checkbox"
                              checked={row.closed}
                              onChange={(e) => updateHoursRow(index, { closed: e.target.checked })}
                              className="h-3.5 w-3.5 accent-brand-500"
                            />
                            Closed
                          </label>
                          {!row.closed && (
                            <div className="flex flex-1 flex-wrap items-center gap-2">
                              <input
                                type="time"
                                value={row.open}
                                onChange={(e) => updateHoursRow(index, { open: e.target.value })}
                                className="h-8 rounded-control border border-line bg-surface-3 px-2 text-xs text-content transition-colors duration-150 focus:border-brand-500 focus:outline-none"
                              />
                              <span className="text-xs text-faint">to</span>
                              <input
                                type="time"
                                value={row.close}
                                onChange={(e) => updateHoursRow(index, { close: e.target.value })}
                                className="h-8 rounded-control border border-line bg-surface-3 px-2 text-xs text-content transition-colors duration-150 focus:border-brand-500 focus:outline-none"
                              />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                    {summarizeOperatingHours(profile.operatingHours).map((line) => (
                      <div
                        key={line.label}
                        className="flex items-center justify-between rounded-control border border-line bg-surface-2 px-3 py-2 text-xs"
                      >
                        <span className="font-medium text-content">{line.label}</span>
                        <span className={line.hours === 'Closed' ? 'text-faint' : 'text-muted'}>
                          {line.hours}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card.Body>
          </Card>

          {/* Capacity + requirements */}
          <Card>
            <Card.Header
              icon={PackageCheck}
              title="Capacity & Requirements"
              subtitle="How much you can handle, and anything partners should know"
            />
            <Card.Body className="space-y-4">
              {editing ? (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Input
                    label="Capacity"
                    type="number"
                    min="0"
                    step="1"
                    value={draft.capacity.value}
                    onChange={(e) => updateCapacity('value', e.target.value)}
                    error={errors.capacity}
                  />
                  <Input
                    label="Capacity unit"
                    value={draft.capacity.unit}
                    onChange={(e) => updateCapacity('unit', e.target.value)}
                    hint="e.g. meals / day, units / week"
                  />
                </div>
              ) : (
                <ProfileField
                  label="Capacity"
                  value={
                    profile.capacity?.value !== '' && profile.capacity?.value != null
                      ? `${profile.capacity.value} ${profile.capacity.unit ?? ''}`.trim()
                      : 'Not specified'
                  }
                />
              )}

              {editing ? (
                <Textarea
                  label="Requirements & notes"
                  rows={3}
                  value={draft.requirements}
                  onChange={(e) => updateField('requirements', e.target.value)}
                  hint="Storage, packaging, pickup or delivery requirements, etc."
                />
              ) : (
                <ProfileField label="Requirements & notes" value={profile.requirements || 'None specified.'} />
              )}
            </Card.Body>
          </Card>
        </div>

        <div className="space-y-6 lg:space-y-8">
          {/* Supported resource types */}
          <Card>
            <Card.Header title="Supported Resource Types" subtitle="What your organization can send or receive" />
            <Card.Body>
              {errors.resourceTypes && (
                <p className="mb-2 text-xs text-critical">{errors.resourceTypes}</p>
              )}

              {editing ? (
                <div className="space-y-2">
                  {Object.values(RESOURCE_TYPE).map((type) => {
                    const meta = RESOURCE_META[type];
                    const Icon = RESOURCE_ICONS[type];
                    const checked = draft.resourceTypes.includes(type);
                    return (
                      <label
                        key={type}
                        className={cn(
                          'flex cursor-pointer items-center gap-3 rounded-control border border-line bg-surface-2 p-3',
                          'transition-colors duration-150 hover:border-line-strong',
                          'has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500/40',
                          'has-[:checked]:ring-1',
                          type === RESOURCE_TYPE.FOOD
                            ? 'has-[:checked]:border-food has-[:checked]:ring-food/30'
                            : 'has-[:checked]:border-medical has-[:checked]:ring-medical/30',
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleResourceType(type)}
                          className="h-4 w-4 accent-brand-500"
                        />
                        {Icon && (
                          <Icon
                            size={16}
                            strokeWidth={1.75}
                            className={type === RESOURCE_TYPE.FOOD ? 'text-food' : 'text-medical'}
                          />
                        )}
                        <span className="text-sm font-medium text-content">{meta.label}</span>
                      </label>
                    );
                  })}
                </div>
              ) : profile.resourceTypes.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {profile.resourceTypes.map((type) => (
                    <Badge key={type} tone={type} icon={RESOURCE_ICONS[type]}>
                      {RESOURCE_META[type]?.label ?? type}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-faint">No resource types selected.</p>
              )}
            </Card.Body>
          </Card>

          {/* Verification status */}
          <Card>
            <Card.Header icon={ShieldCheck} title="Verification Status" />
            <Card.Body className="space-y-3">
              {verificationMeta ? (
                <>
                  <Badge tone={verificationMeta.tone} icon={VerificationIcon} size="md">
                    {verificationMeta.label}
                  </Badge>
                  <p className="text-xs leading-relaxed text-muted">{verificationMeta.note}</p>
                </>
              ) : (
                <p className="text-xs text-faint">Not evaluated.</p>
              )}
            </Card.Body>
          </Card>
        </div>
      </div>
    </form>
  );
}

/** Heading + description shown above the page, in loading, error and loaded states alike. */
function PageHeader() {
  return (
    <div>
      <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">Organization Profile</h1>
      <p className="mt-1.5 text-sm text-muted">
        Organization details and capabilities — visible to the rescue network when your organization is matched.
      </p>
      <p className="mt-3 rounded-control border border-line bg-surface-2 px-3.5 py-3 text-xs leading-relaxed text-muted">
        There's no backend yet — changes you save here are stored in this browser for your account and are not
        synced anywhere else.
      </p>
    </div>
  );
}

/** One read-only label/value pair, styled to match the app's field layouts. */
function ProfileField({ label, value, icon: Icon, className }) {
  return (
    <div className={cn('min-w-0', className)}>
      <p className="text-[11px] font-medium uppercase tracking-wide text-faint">{label}</p>
      <p className="mt-1 flex items-start gap-1.5 text-sm text-content">
        {Icon && <Icon size={13} strokeWidth={1.75} className="mt-0.5 shrink-0 text-brand-400" />}
        <span className="break-words">{value}</span>
      </p>
    </div>
  );
}
