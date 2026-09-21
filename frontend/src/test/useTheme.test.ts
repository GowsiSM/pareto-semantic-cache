import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTheme } from "../hooks/useTheme";

function mockMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockReturnValue({
    matches,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }) as unknown as typeof window.matchMedia;
}

describe("useTheme", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("defaults to light when no stored preference and system prefers light", () => {
    mockMatchMedia(false);

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });

  it("defaults to dark when system prefers dark and nothing is stored", () => {
    mockMatchMedia(true);

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
  });

  it("toggles between light and dark", () => {
    mockMatchMedia(false);

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");

    act(() => result.current.toggleTheme());
    expect(result.current.theme).toBe("dark");

    act(() => result.current.toggleTheme());
    expect(result.current.theme).toBe("light");
  });

  it("persists the explicit choice to localStorage and applies it to the document element", () => {
    mockMatchMedia(false);

    const { result } = renderHook(() => useTheme());
    act(() => result.current.toggleTheme());

    expect(window.localStorage.getItem("semanticache-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("respects a previously stored preference over the system setting", () => {
    window.localStorage.setItem("semanticache-theme", "dark");
    mockMatchMedia(false); // system says light, but stored preference should win

    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
  });
});
