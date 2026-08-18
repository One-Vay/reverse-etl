import { AlertTriangle } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled UI error:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">
            An unexpected error occurred while rendering this page. Try reloading — if the
            problem persists, check the browser console for details.
          </p>
        </div>
        <Button onClick={() => window.location.reload()}>Reload page</Button>
      </div>
    );
  }
}
