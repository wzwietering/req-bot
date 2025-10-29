"use client";

/**
 * Error boundary for QuotaProvider to prevent full app crashes
 */

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class QuotaErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("QuotaProvider error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // Render children without quota context (quota features will be disabled)
      return this.props.children;
    }

    return this.props.children;
  }
}
