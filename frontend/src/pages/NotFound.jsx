import { Link } from 'react-router-dom';
import { PATHS } from '@/routes/paths';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <p className="font-mono text-sm text-faint">404</p>
      <h1 className="text-2xl font-semibold tracking-tight">This route does not exist</h1>
      <p className="max-w-sm text-sm text-muted">
        The page you are looking for is not part of the rescue network.
      </p>
      <Link
        to={PATHS.DASHBOARD}
        className="rounded-control bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-500"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
