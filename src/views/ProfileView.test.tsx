import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProfileView } from "./ProfileView";

const profileData = {
  n: "Test User",
  s: "Software Engineer building cool stuff",
  skills: [
    { id: "sk1", n: "React", cat: "frontend" },
  ],
  exp: [
    { id: "ex1", role: "Senior Engineer", co: "Acme Corp", period: "2020-2024", d: "Built things" },
  ],
  projects: [
    { id: "pr1", title: "My Project", stack: "React,Node", impact: "Great success", repo: "" },
  ],
};

function okResponse(body?: unknown): Response {
  return new Response(JSON.stringify(body ?? {}), { status: 200 });
}

function errResponse(status: number, detail?: string): Response {
  return new Response(JSON.stringify(detail ? { detail } : undefined), { status });
}

function makeApi() {
  const fn = vi.fn<(path: string, opts?: RequestInit) => Promise<Response>>();
  fn.mockImplementation(() => Promise.resolve(okResponse(profileData)));
  return fn;
}

async function renderView(api?: (path: string, opts?: RequestInit) => Promise<Response>) {
  const def = makeApi();
  const comp = render(<ProfileView api={api ?? def} setView={vi.fn()} />);
  await waitFor(() => {
    expect(screen.getByText("1 SKILLS")).toBeInTheDocument();
  });
  return { ...comp, api: api ?? def, setView: vi.fn() };
}

describe("ProfileView — deleteItem error visibility", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows error when skill delete fails with 500", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { api } = await renderView();
    api.mockReturnValueOnce(Promise.resolve(errResponse(500)));
    fireEvent.click(screen.getByTitle("Delete skill"));
    await waitFor(() => {
      expect(screen.getByText(/Delete failed.*500/i)).toBeInTheDocument();
    });
  });

  it("does not show error when skill delete succeeds", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { api } = await renderView();
    api.mockReturnValueOnce(Promise.resolve(okResponse({ ok: true })));
    fireEvent.click(screen.getByTitle("Delete skill"));
    await waitFor(() => {
      expect(screen.queryByText(/Delete failed/i)).not.toBeInTheDocument();
    });
  });

  it("shows server detail in error for 422 delete", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { api } = await renderView();
    api.mockReturnValueOnce(Promise.resolve(errResponse(422, "Cannot delete core skill")));
    fireEvent.click(screen.getByTitle("Delete skill"));
    await waitFor(() => {
      expect(screen.getByText("Cannot delete core skill")).toBeInTheDocument();
    });
  });

  it("clears error on retry after delete failure", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { api } = await renderView();
    api.mockReturnValueOnce(Promise.resolve(errResponse(500)));
    fireEvent.click(screen.getByTitle("Delete skill"));
    await waitFor(() => {
      expect(screen.getByText(/Delete failed.*500/i)).toBeInTheDocument();
    });
    api.mockReturnValueOnce(Promise.resolve(okResponse({ ok: true })));
    fireEvent.click(screen.getByTitle("Delete skill"));
    await waitFor(() => {
      expect(screen.queryByText(/Delete failed.*500/i)).not.toBeInTheDocument();
    });
  });

  it("shows fallback message when delete fails with no detail", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { api } = await renderView();
    api.mockRejectedValueOnce(new Error(""));
    fireEvent.click(screen.getByTitle("Delete skill"));
    await waitFor(() => {
      expect(screen.getByText("Failed to delete item")).toBeInTheDocument();
    });
  });
});

describe("ProfileView — saveEdit error visibility", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  async function openExpEdit() {
    fireEvent.click(screen.getByText("Experience", { selector: "span" }));
    const editBtns = document.querySelectorAll<HTMLButtonElement>(".profile-mini-action");
    const editExpBtn = editBtns[0];
    expect(editExpBtn).toBeTruthy();
    expect(editExpBtn.className).not.toContain("profile-danger");
    fireEvent.click(editExpBtn);
    return await screen.findByRole("button", { name: "Save" });
  }

  it("shows error when experience save fails with 500", async () => {
    const { api } = await renderView();
    const saveBtn = await openExpEdit();
    api.mockReturnValueOnce(Promise.resolve(errResponse(500)));
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.getByText(/Save failed.*500/i)).toBeInTheDocument();
    });
  });

  it("shows server detail on 422 save edit", async () => {
    const { api } = await renderView();
    const saveBtn = await openExpEdit();
    api.mockReturnValueOnce(Promise.resolve(errResponse(422, "Role description too short")));
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.getByText("Role description too short")).toBeInTheDocument();
    });
  });
});

describe("ProfileView — saveCandidate error visibility", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  async function openCandidateEdit() {
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    return await screen.findByRole("button", { name: /Save Identity/ });
  }

  it("shows error when candidate save fails with 500", async () => {
    const { api } = await renderView();
    const saveBtn = await openCandidateEdit();
    api.mockReturnValueOnce(Promise.resolve(errResponse(500)));
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.getByText(/Save failed.*500/i)).toBeInTheDocument();
    });
  });

  it("shows server detail on 422 save candidate", async () => {
    const { api } = await renderView();
    const saveBtn = await openCandidateEdit();
    api.mockReturnValueOnce(Promise.resolve(errResponse(422, "Name must not be empty")));
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.getByText("Name must not be empty")).toBeInTheDocument();
    });
  });

  it("clears error on retry after saveCandidate failure", async () => {
    const { api } = await renderView();
    const saveBtn = await openCandidateEdit();
    api.mockReturnValueOnce(Promise.resolve(errResponse(500)));
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.getByText(/Save failed.*500/i)).toBeInTheDocument();
    });
    api.mockReturnValueOnce(Promise.resolve(okResponse({ ok: true })));
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.queryByText(/Save failed.*500/i)).not.toBeInTheDocument();
    });
  });

  it("shows fallback when fetch throws with no message in saveCandidate", async () => {
    const { api } = await renderView();
    const saveBtn = await openCandidateEdit();
    api.mockRejectedValueOnce(new Error(""));
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.getByText("Failed to save identity")).toBeInTheDocument();
    });
  });
});
