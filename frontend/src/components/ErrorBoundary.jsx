import { Component } from 'react';

import { ErrorState } from '@/components/ui';

/**
 * Catches an error thrown while rendering anything below it and shows a
 * message with a retry, instead of React unmounting the whole tree (which
 * leaves a blank screen). AppLayout keys it by route, so moving to another
 * page always starts clean.
 */
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary] Render error:', error, info?.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="panel">
        <ErrorState
          title="This page hit an unexpected error"
          description="Something went wrong while showing this page. Try again, or open another page from the menu."
          onRetry={this.reset}
          retryLabel="Try again"
        />
      </div>
    );
  }
}
