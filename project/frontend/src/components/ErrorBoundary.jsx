// Catches render errors so one bad screen does not blank the whole app.
//
// Without this a thrown error during a demo leaves an empty white page with
// nothing to click. Resetting on navigation means the user can leave the broken
// screen rather than reloading.

import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidMount() {
    this.onHashChange = () => {
      if (this.state.error) this.setState({ error: null });
    };
    window.addEventListener("hashchange", this.onHashChange);
  }

  componentWillUnmount() {
    window.removeEventListener("hashchange", this.onHashChange);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="page">
        <div className="card">
          <div className="card-title">This screen failed to render</div>
          <div className="alert error mono tiny">
            {String(this.state.error?.message || this.state.error)}
          </div>
          <div className="row">
            <a className="btn" href="#/dashboard">
              Dashboard
            </a>
            <button onClick={() => this.setState({ error: null })}>Retry</button>
          </div>
        </div>
      </div>
    );
  }
}
