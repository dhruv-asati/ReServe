import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  User,
  Building2,
  Mail,
  Lock,
  Eye,
  EyeOff,
  Sparkles,
  ShieldCheck,
  UserPlus,
} from 'lucide-react';

import { Button, Input, Select, Badge } from '@/components/ui';
import { PATHS } from '@/routes/paths';
import { useAuth } from '@/context/AuthContext';

/**
 * Register — org onboarding for providers, recipients, and rescue partners.
 *
 * On submit, services/auth.js registers the account with the backend
 * (POST /auth/register), signs it in, and saves the organization name to the
 * profile (PUT /users/me) — see AuthContext.
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const ROLE_OPTIONS = [
  { value: 'provider', label: 'Provider' },
  { value: 'recipient', label: 'Recipient' },
  { value: 'rescue-partner', label: 'Rescue Partner' },
];

const INITIAL_FORM = {
  name: '',
  organization: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: '',
};

function validate({ name, organization, email, password, confirmPassword, role }) {
  const errors = {};

  if (!name.trim()) errors.name = 'Name is required.';
  if (!organization.trim()) errors.organization = 'Organization name is required.';

  if (!email.trim()) {
    errors.email = 'Email is required.';
  } else if (!EMAIL_RE.test(email.trim())) {
    errors.email = 'Enter a valid email address.';
  }

  if (!password) {
    errors.password = 'Password is required.';
  } else if (password.length < 8) {
    errors.password = 'Use at least 8 characters.';
  }

  if (!confirmPassword) {
    errors.confirmPassword = 'Confirm your password.';
  } else if (password && confirmPassword !== password) {
    errors.confirmPassword = 'Passwords do not match.';
  }

  if (!role) errors.role = 'Select a role.';

  return errors;
}

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [form, setForm] = useState(INITIAL_FORM);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  function updateField(field, value) {
    const next = { ...form, [field]: value };
    setForm(next);
    if (touched[field] || (field === 'password' && touched.confirmPassword)) {
      setErrors(validate(next));
    }
  }

  function handleBlur(field) {
    setTouched((prev) => ({ ...prev, [field]: true }));
    setErrors(validate(form));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');
    setTouched({
      name: true,
      organization: true,
      email: true,
      password: true,
      confirmPassword: true,
      role: true,
    });

    const nextErrors = validate(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await register({
        name: form.name,
        organization: form.organization,
        email: form.email,
        password: form.password,
        role: form.role,
      });
      navigate(PATHS.DASHBOARD, { replace: true });
    } catch (err) {
      setFormError(err?.message ?? 'Something went wrong creating your account. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="grid-backdrop pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />

      <div className="relative mx-auto grid min-h-screen max-w-6xl grid-cols-1 items-center gap-10 px-4 py-10 sm:px-6 lg:grid-cols-2 lg:gap-16 lg:px-8">
        {/* ---------- Form column ---------- */}
        <div className="animate-fade-up mx-auto w-full max-w-sm">
          <Link to={PATHS.LANDING} className="inline-flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-control bg-brand-600/15 text-brand-400 ring-1 ring-inset ring-brand-500/20">
              <Sparkles size={15} strokeWidth={2} />
            </span>
            <span className="text-sm font-semibold tracking-tight text-content">ReServe</span>
          </Link>

          <h1 className="mt-7 text-2xl font-bold tracking-tight text-content sm:text-3xl">
            Create your account
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Register your organization to coordinate rescues, matching, and live operations.
          </p>

          <form className="mt-7 space-y-4" onSubmit={handleSubmit} noValidate>
            <Input
              label="Name"
              type="text"
              icon={User}
              placeholder="Jordan Rivera"
              autoComplete="name"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              onBlur={() => handleBlur('name')}
              error={touched.name ? errors.name : undefined}
            />

            <Input
              label="Organization Name"
              type="text"
              icon={Building2}
              placeholder="Riverside Community Kitchen"
              autoComplete="organization"
              value={form.organization}
              onChange={(e) => updateField('organization', e.target.value)}
              onBlur={() => handleBlur('organization')}
              error={touched.organization ? errors.organization : undefined}
            />

            <Input
              label="Email"
              type="email"
              icon={Mail}
              placeholder="you@organization.org"
              autoComplete="email"
              value={form.email}
              onChange={(e) => updateField('email', e.target.value)}
              onBlur={() => handleBlur('email')}
              error={touched.email ? errors.email : undefined}
            />

            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                icon={Lock}
                placeholder="At least 8 characters"
                autoComplete="new-password"
                value={form.password}
                onChange={(e) => updateField('password', e.target.value)}
                onBlur={() => handleBlur('password')}
                error={touched.password ? errors.password : undefined}
                className="pr-9"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
                className="absolute right-3 top-[34px] text-faint transition-colors hover:text-muted"
              >
                {showPassword ? (
                  <EyeOff size={15} strokeWidth={1.75} />
                ) : (
                  <Eye size={15} strokeWidth={1.75} />
                )}
              </button>
            </div>

            <div className="relative">
              <Input
                label="Confirm Password"
                type={showConfirmPassword ? 'text' : 'password'}
                icon={Lock}
                placeholder="Re-enter your password"
                autoComplete="new-password"
                value={form.confirmPassword}
                onChange={(e) => updateField('confirmPassword', e.target.value)}
                onBlur={() => handleBlur('confirmPassword')}
                error={touched.confirmPassword ? errors.confirmPassword : undefined}
                className="pr-9"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword((v) => !v)}
                aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showConfirmPassword}
                className="absolute right-3 top-[34px] text-faint transition-colors hover:text-muted"
              >
                {showConfirmPassword ? (
                  <EyeOff size={15} strokeWidth={1.75} />
                ) : (
                  <Eye size={15} strokeWidth={1.75} />
                )}
              </button>
            </div>

            <Select
              label="Role"
              placeholder="Select your role"
              options={ROLE_OPTIONS}
              value={form.role}
              onChange={(e) => updateField('role', e.target.value)}
              onBlur={() => handleBlur('role')}
              error={touched.role ? errors.role : undefined}
            />

            {formError && (
              <p className="rounded-control border border-critical/30 bg-critical/10 px-3 py-2 text-xs text-critical">
                {formError}
              </p>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={submitting}
              icon={submitting ? undefined : UserPlus}
              className="w-full justify-center"
            >
              {submitting ? 'Creating account…' : 'Register'}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-muted">
            Already have an account?{' '}
            <Link
              to={PATHS.LOGIN}
              className="font-medium text-brand-400 transition-colors hover:text-brand-300"
            >
              Login
            </Link>
          </p>
        </div>

        {/* ---------- Visual column (desktop only) ---------- */}
        <div className="animate-fade-up mx-auto hidden w-full max-w-md lg:mx-0 lg:block lg:max-w-none">
          <div className="panel relative overflow-hidden p-8">
            <div className="pointer-events-none absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-500/10 blur-3xl" />

            <div className="relative">
              <div className="mb-5 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-faint">
                  Join the network
                </span>
                <Badge tone="active" dot size="sm">
                  Live coordination
                </Badge>
              </div>

              <div className="flex flex-col items-center py-10 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-600/15 text-brand-400 ring-1 ring-inset ring-brand-500/20">
                  <ShieldCheck size={28} strokeWidth={1.75} />
                </div>
                <p className="mt-5 max-w-xs text-sm leading-relaxed text-muted">
                  Every account joins as a Provider, Recipient, or Rescue Partner — matching
                  and routing adapt to that role from day one.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2 border-t border-line pt-4">
                {ROLE_OPTIONS.map((option) => (
                  <div
                    key={option.value}
                    className="rounded-control border border-line bg-surface-2 py-2 text-center text-[11px] font-medium text-muted"
                  >
                    {option.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
