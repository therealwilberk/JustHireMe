import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SettingsModal from "./SettingsModal";

function ok(body?: unknown): Response {
  return new Response(JSON.stringify(body ?? {}), { status: 200 });
}

function err(status: number, detail?: string): Response {
  return new Response(JSON.stringify(detail ? { detail } : undefined), { status });
}

function makeApi() {
  const fn = vi.fn<(path: string, opts?: RequestInit) => Promise<Response>>();
  fn.mockReturnValue(Promise.resolve(ok({ llm_provider: "ollama" })));
  return fn;
}

function renderModal(api?: (path: string, opts?: RequestInit) => Promise<Response>) {
  const def = makeApi();
  return {
    ...render(<SettingsModal api={api ?? def} onClose={vi.fn()} />),
    api: api ?? def,
    onClose: vi.fn(),
  };
}

async function getSaveButton() {
  return await screen.findByRole("button", { name: /save settings/i });
}

describe("SettingsModal save flow — error visibility", () => {
  it("shows error when API returns 500", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.resolve(err(500)));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/Save failed.*500/i)).toBeInTheDocument();
    });
  });

  it("shows server detail message on 422", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.resolve(err(422, "Invalid provider key")));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText("Invalid provider key")).toBeInTheDocument();
    });
  });

  it("does NOT show 'Saved' when save fails", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.resolve(err(500)));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.queryByText(/Saved/)).not.toBeInTheDocument();
    });
  });

  it("shows fallback error message when response has no detail", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.resolve(err(503)));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/Save failed.*503/i)).toBeInTheDocument();
    });
  });

  it("clears error and shows 'Saved' on retry after failure", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.resolve(err(500)));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/Save failed.*500/i)).toBeInTheDocument();
    });
    api.mockReturnValueOnce(Promise.resolve(ok()));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.queryByText(/Save failed.*500/i)).not.toBeInTheDocument();
    });
    expect(screen.getByText(/Saved/)).toBeInTheDocument();
  });

  it("shows 'Saved' on successful save", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.resolve(ok()));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/Saved/)).toBeInTheDocument();
    });
  });

  it("resets loading indicator after failure", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.resolve(err(500)));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /save settings/i })).not.toBeDisabled();
    });
  });

  it("clears stale 'Saved' from previous success after subsequent failure", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.resolve(ok()));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/Saved/)).toBeInTheDocument();
    });
    api.mockReturnValueOnce(Promise.resolve(err(500)));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.queryByText(/Saved/)).not.toBeInTheDocument();
    });
  });

  it("shows error when fetch throws (network error)", async () => {
    const api = makeApi();
    api.mockReturnValueOnce(Promise.resolve(ok({ llm_provider: "ollama" })));
    render(<SettingsModal api={api} onClose={vi.fn()} />);
    const btn = await getSaveButton();
    api.mockReturnValueOnce(Promise.reject(new Error("Network disconnected")));
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText("Network disconnected")).toBeInTheDocument();
    });
  });
});
