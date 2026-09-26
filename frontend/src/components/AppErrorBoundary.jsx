import { Component } from "react";

export class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <main role="alert" className="min-h-screen bg-obsidian px-5 py-20 text-linen" data-testid="app-error-boundary">
          <h1 className="font-heading text-4xl">This page could not be shown.</h1>
          <p className="mt-4">Reload HawkVision Homes. No account action was completed.</p>
        </main>
      );
    }
    return this.props.children;
  }
}
