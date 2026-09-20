import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, ShieldCheck, Sparkles, LogIn } from 'lucide-react';

import { Button, Input, Badge } from '@/components/ui';
import { PATHS } from '@/routes/paths';
import { useAuth } from '@/context/AuthContext';
import useLocalStorage from '@/hooks/useLocalStorage';

/**
 * Login — organization sign-in.
 *
 * Credentials are checked by the ReServe backend (POST /auth/login) through
 * AuthContext -> services/auth.js, which stores the JWT tokens and the
 * signed-in user.
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate({ email, password }) {
  const errors = {};
  if (!email.trim()) {
    errors.email = 'Email is required.';
  } else if (!EMAIL_RE.test(email.trim())) {
    errors.email = 'Enter a valid email address.';
  }

  if (!password) {
    errors.password = 'Password is required.';
  }

  return errors;
}

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const redirectTo = location.state?.from ?? PATHS.DASHBOARD;

  const [remembered, setRemembered] = useLocalStorage('reserve.rememberedEmail', '');

  const [form, setForm] = useState({ email: remembered ?? '', password: '' });
  const [remember, setRemember] = useState(Boolean(remembered));
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (touched[field]) {
      setErrors(validate({ ...form, [field]: value }));
    }
  }

  function handleBlur(field) {
    setTouched((prev) => ({ ...prev, [field]: true }));
    setErrors(validate(form));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');
    setTouched({ email: true, password: true });

    const nextErrors = validate(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await login({ email: form.email.trim(), password: form.password });
      setRemembered(remember ? form.email.trim() : '');
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setFormError(err?.message ?? 'Something went wrong signing you in. Please try again.');
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
            Welcome back
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Sign in to coordinate rescues, matching, and live operations.
          </p>

          <form className="mt-7 space-y-4" onSubmit={handleSubmit} noValidate>
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

            <div>
              <div className="relative">
                <Input
                  label="Password"
                  type={showPassword ? 'text' : 'password'}
                  icon={Lock}
                  placeholder="••••••••"
                  autoComplete="current-password"
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
            </div>

            <div className="flex items-center justify-between pt-0.5">
              <label className="inline-flex select-none items-center gap-2 text-xs text-muted">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-3.5 w-3.5 rounded-[4px] border border-line-strong bg-surface-2 accent-brand-500"
                />
                Remember me
              </label>

              <button
                type="button"
                onClick={() => setFormError('Password reset is not available yet.')}
                className="text-xs font-medium text-brand-400 transition-colors hover:text-brand-300"
              >
                Forgot password?
              </button>
            </div>

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
              icon={submitting ? undefined : LogIn}
              className="w-full justify-center"
            >
              {submitting ? 'Signing in…' : 'Log In'}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-muted">
            Don&rsquo;t have an account?{' '}
            <Link
              to={PATHS.REGISTER}
              className="font-medium text-brand-400 transition-colors hover:text-brand-300"
            >
              Create one
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
                  Secure access
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
                  Your sign-in keeps rescue coordination, matching, and live operations
                  tied to your organization.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2 border-t border-line pt-4">
                {['Providers', 'Matching', 'Recipients'].map((label) => (
                  <div
                    key={label}
                    className="rounded-control border border-line bg-surface-2 py-2 text-center text-[11px] font-medium text-muted"
                  >
                    {label}
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
