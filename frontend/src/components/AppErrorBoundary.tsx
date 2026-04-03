import { Component, ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
  message: string;
};

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : "Unexpected UI failure"
    };
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="panel">
          <h2>Something broke in this view</h2>
          <p className="muted">{this.state.message}</p>
        </section>
      );
    }
    return this.props.children;
  }
}
