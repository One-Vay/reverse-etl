import { useEffect, type RefObject } from "react";

/**
 * Calls `onOutsideClick` when a pointer event lands outside `ref`'s element.
 *
 * Deliberately not implemented with onBlur+setTimeout: that pattern races a
 * fixed timer against how long the user takes to move the mouse onto the
 * menu item, so it can close the menu before a real (non-instant) click
 * lands. Listening for the actual click location has no such race.
 */
export function useClickOutside(
  ref: RefObject<HTMLElement>,
  enabled: boolean,
  onOutsideClick: () => void,
) {
  useEffect(() => {
    if (!enabled) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (!ref.current) return;
      if (!ref.current.contains(event.target as Node)) {
        onOutsideClick();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [ref, enabled, onOutsideClick]);
}
