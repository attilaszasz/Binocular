## Research Report

**Context**: Binocular's Modules page (E008) shows cards with static module info. E026 adds an editable per-module check frequency field. The backend already serves per-device-type schedules via `PUT /api/v1/schedules/device-types/{id}` with `intervalMinutes` (range 1–10080), and per ADR-0009 device_type_id equals module_id. The backend scheduling is already per-module, but no frequency data is surfaced on the Modules page.

## UX Patterns: Inline Cell Editing with Dropdown/Select Inputs

Click-to-edit with a native `<select>` that auto-commits on value change is the recommended pattern. Show a subtle edit affordance: a pencil icon on hover with `cursor: pointer` and a dashed underline beneath the frequency label. Escape cancels without saving. Show a spinner adjacent to the frequency field during the API save operation; on success, replace the spinner with a brief checkmark (~2 seconds) that fades out. Avoid two-step confirm (select value then click Save) — it adds a click for zero safety gain. For card-based layouts, display current interval as text; toggle into a `<select>` on click or edit icon click. Editor open/close uses a 150ms opacity fade transition; the card layout height adjusts immediately (no animation) to avoid layout shift jank.

Sources: W3C ARIA Authoring Practices Data Grid Example 2 (editable-cell-with-dropdown pattern), React Aria ToggleButtonGroup documentation.

## Best Practices: Frequency/Interval Picker Components

Use a segmented-control preset pattern: a row of buttons offering common intervals (1h, 6h, 12h, 24h) plus a "Custom" option that reveals a number input constrained to 1–10080 minutes. Render within each module card. Avoid free-form text without presets (users calculate minutes mentally). Always show human-readable labels ("12h") alongside raw minute values. React Aria's `ToggleButtonGroup` with `selectionMode="single"` provides the accessible foundation.

Sources: React Aria ToggleButtonGroup documentation, common scheduling tool patterns.

## React/Tailwind Inline Editing with TanStack Query Persistence

Use `useMutation` wrapping `updateSchedule(moduleId, payload)` with `onSuccess` → `queryClient.invalidateQueries(['schedules'])`. Track `editingModuleId` in parent state. Each card conditionally renders text display or the `<select>` + preset buttons. For dropdown selects (single fire on change), no debounce needed. Show loading state during save, revert on error. Keep mutation logic in a custom hook.

Sources: TanStack Query mutation guide (invalidation via queryClient.invalidateQueries), TkDodo's "Mastering Mutations in React Query" (prefer invalidation over direct cache writes).

## Inline Validation Messages

Custom input validation error messages:
- Out of range (< 1 or > 10080): "Must be between 1 and 10,080 minutes"
- Non-integer: "Must be a whole number"
- Error text appears below the input field in red (`text-red-600 text-sm`), programmatically associated via `aria-describedby`.

## External Change Notification

When schedule data changes externally while the editor is open (US2-9):
- Content: "This schedule was changed elsewhere. The editor will close."
- Placement: A notification banner at the top of the editor panel (inside the card), styled with a neutral background (`bg-amber-50 border border-amber-200`).
- Auto-dismiss: The notification auto-dismisses after 5 seconds, and the editor closes, reverting to display mode showing the updated value.
- The closed editor shows the newly-updated value (not the operator's pending edit).

## Save Timeout Indicator

If a save operation takes longer than 3 seconds, the spinner is joined by a "Saving…" text label. If the save exceeds 10 seconds, the UI treats it as a likely failure and shows "Taking longer than expected. You may close the editor — the change will apply when complete." The editor remains open but the operator can dismiss it.

## Accessibility & UX Specifications

### Keyboard Accessibility
The frequency display and editor MUST be fully keyboard accessible:
- **Tab**: Focus moves to the frequency display element on each card.
- **Enter / Space**: Opens the inline editor (preset buttons, custom input, toggle) and moves focus to the first preset button.
- **Arrow keys**: Navigate between preset buttons (Left/Right arrows) within the ToggleButtonGroup.
- **Escape**: Closes the editor without saving and returns focus to the display element (per US2-7).
- **Tab within editor**: Focus moves from presets → custom input → toggle → (if applicable) save button, then out of the editor.

### Focus Management
- On editor open: focus moves into the editor to the first preset button (or the currently-selected preset).
- On editor close (save, cancel, Escape, blur): focus returns to the frequency display element on the card.
- On external change notification: focus moves to the notification banner; after auto-dismiss, focus returns to the display element.

### ARIA Roles & Labels
- **Preset buttons**: Use React Aria `ToggleButtonGroup` with `selectionMode="single"`, which provides `role="radiogroup"` on the container and `role="radio"` on each button. Each button announces its label (e.g., "1h, selected").
- **Custom input**: The number input field MUST have a visible `<label>` ("Custom interval in minutes") and `aria-describedby` pointing to help text: "Enter a whole number between 1 and 10,080". On validation error, the error element's `id` is appended to `aria-describedby`.
- **Enable/disable toggle**: Use the existing application Toggle component for visual and behavioral consistency. The toggle MUST be keyboard operable (Space to toggle) and announce its state via `aria-label` (e.g., "Automatic checking: on" / "Automatic checking: off") and `role="switch"` with `aria-checked`.

### Live Regions & Status Announcements
- **Loading state**: The skeleton for the frequency field is not announced (inert during load). When schedule data arrives, the updated label is rendered — no special announcement needed (the card content is part of normal page flow).
- **Error state (load failure)**: The "Failed to load" error indicator is placed in a live region (`aria-live="polite"`) so screen readers announce it when it appears. The retry button is focusable.
- **Save success**: The checkmark confirmation uses `role="status"` (not `alert`) to avoid interrupting the operator — it's informational.
- **API error toast**: The error toast uses `role="alert"` so screen readers immediately announce the failure message.
- **External change notification**: The notification banner uses `role="alert"` (it's urgent — the operator's pending edit is stale).

### Color Contrast
All text elements in the frequency field MUST meet WCAG AA contrast ratios (4.5:1 for normal text, 3:1 for large text):
- **Frequency label (idle state)**: Sufficient contrast against the card background — achieved by using the Tailwind default text color on the card's background.
- **Preset buttons**: Selected button uses a high-contrast filled style (e.g., `bg-blue-600 text-white`); unselected buttons use outlined style (`border border-gray-300 text-gray-700`). Both meet AA contrast.
- **Validation error text**: Red text (`text-red-600`) on card background — verify ≥4.5:1 contrast ratio.
- **Custom input border**: Error state adds a red border (`border-red-500`) as a secondary indicator (not relying on color alone).

### Summary

The Modules page card grid needs a click-to-edit frequency control: preset buttons mapping to interval_minutes, using `useMutation` around the existing `updateSchedule()` API. The backend schedule infrastructure is already per-module. The Modules API response may need to include schedule data (interval, enabled status) so the page can display it without a separate query.
