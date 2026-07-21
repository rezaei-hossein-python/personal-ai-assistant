# Accessibility Guide

Personal AI Assistant is designed and tested toward WCAG 2.2 Level AA where applicable. This is practical product accessibility guidance and validation, not a formal WCAG conformance certification.

## Scope

Phase 13 covers the React web UI and the packaged Windows desktop UI rendered through `pywebview`. The work preserves Backend Core v1, Frontend v1, Knowledge/RAG v1, Long-Term Memory v1, Conversation History v1, Actions & Tools v1, Deployment & Production Hardening v1, and Windows Desktop Application v1.

Microsoft 365 integrations, Word add-ins, and unrelated product features are out of scope for this phase.

## Audit Findings

- Semantic: history needed a navigation landmark and the chat area needed one top-level `main`.
- Keyboard: native controls were mostly present, but repeated controls needed clearer names and focus restoration.
- Focus: New Chat, conversation deletion, memory save, and memory deletion did not move focus predictably.
- Screen reader: backend, upload, memory, key, and chat completion states needed restrained announcements.
- Contrast: secondary text, active conversation metadata, and user-message role text needed AA-oriented adjustment.
- Status/announcement: counts and document states needed meaningful context.
- Form labeling: several errors were not programmatically associated with fields.
- Responsive/reflow: compact layouts needed more wrapping at narrow widths and 200% zoom.
- Destructive-action UX: conversation delete, memory delete, and OpenAI key removal needed clearer confirmation.
- Desktop-specific accessibility: focus rings and skip navigation needed to work in browser and `pywebview`.

## Semantic HTML

The UI uses native HTML controls and landmarks first: `main`, `header`, `nav`, `section`, `form`, `label`, `input`, `select`, `button`, `ul`, and `li`.

ARIA is used only where native semantics need extra context, such as unique labels for repeated delete buttons, `aria-describedby` error/helper wiring, `aria-current`, live regions, and busy states.

## Keyboard Model

All major controls are reachable through normal tab order without positive `tabindex`. Native controls handle Enter, Space, and arrow-key behavior. Browser-native confirmation dialogs provide keyboard-accessible confirmation and Escape cancellation.

## Focus Management

- New Chat moves focus to the message input.
- Deleting a conversation moves focus to the next conversation, previous conversation, or New Chat.
- Saving a memory clears key/value and returns focus to the memory key field.
- Deleting a memory moves focus to the next memory, previous memory, or the Memories heading.
- Authentication validation focuses the first invalid field for client-side errors.
- Desktop key actions preserve logical focus on the invoking control.

No custom focus trap is implemented because no custom modal dialog is used in this phase.

## Screen Reader Behavior

Visible labels are preserved for message authors, forms, controls, statuses, and document/memory lists. Repeated controls receive unique accessible names such as `Delete conversation: <label>` and `Delete memory: <category> / <key>`.

Assistant and user messages are separate articles with author labels. Tool metadata, memory use, knowledge warnings, and citations are represented as text, not color alone.

## Live Regions

The app uses polite announcements for backend connectivity, authentication status, session expiry, new chat readiness, assistant response completion, document upload results, memory save/delete results, and OpenAI key save/test/remove results. Urgent errors use visible text with `role="alert"`.

The conversation history is not a constantly updating assertive live region.

## Errors And Validation

Field-specific helper/error text is associated with controls through `aria-describedby`; invalid fields use `aria-invalid` when applicable. Errors remain visible and are not communicated only by color.

Covered areas include authentication, Desktop Settings, Documents, Memory, Chat, backend availability, and session expiry.

## Contrast

Phase 13 uses axe color-contrast checks against representative auth and main app screens. Fixed contrast issues included secondary/count text on light panels, active conversation message count text, disabled primary button text, user-message author label opacity, and transparent input backgrounds.

Status badges include text such as `Document processing completed`, not only color.

## Zoom And Reflow

The layout uses flexible grids, wrapping text, and responsive breakpoints. At narrow widths and high zoom, workspace areas stack, settings and memory forms wrap, chat input stacks vertically, message bubbles constrain to available width, and paths/filenames/memory values wrap instead of clipping.

Target validation is 200% browser zoom without loss of essential functionality.

## Reduced Motion

The stylesheet includes a `prefers-reduced-motion: reduce` rule that minimizes non-essential animation and transition durations. Current UI motion is minimal.

## Destructive Actions

Delete conversation, Delete memory, and Remove OpenAI API key have target-specific accessible names and confirmation. Existing backend/tool safety behavior is unchanged.

## Automated Tooling

Run the automated accessibility checks:

```cmd
cd frontend
npm.cmd run test:a11y
```

Tooling selected:

- `@axe-core/playwright` for WCAG-oriented automated rule checks
- Playwright Chromium for rendering the real built React UI
- a small Node runner that starts Vite preview, mocks `/api/*`, runs checks, and exits reliably on Windows

Automated coverage includes authentication, the authenticated app shell, Desktop Settings, Memory, Documents, a representative conversation, and skip-link keyboard focus.

## Narrator Validation

Manual Windows Narrator checklist:

- Authentication: Sign in/Create account headings announce; fields have names; validation errors announce.
- Main UI: landmarks/headings are meaningful; Skip to conversation works; History is navigable.
- Chat: messages announce You/Assistant; response completion is announced; citations are understandable.
- Documents: file input is labeled; selected file and upload status are announced.
- Memory: form controls are labeled; saved memories are understandable; delete controls identify targets.
- Desktop Settings: OpenAI key status announces configured/not configured; Save key, Test key, and Remove key are clear.
- Focus: visible focus corresponds to Narrator focus where practical.

Narrator testing is manual because it cannot be fully automated in the current project test setup.

## NVDA Follow-Up

NVDA installation is not required to complete Phase 13. Recommended future NVDA verification: landmarks, heading navigation, form mode behavior, button names, conversation navigation, live-region announcements, destructive confirmations, and citation/metadata reading order.

## Known Limitations

- Browser-native confirmation dialogs are used; appearance varies by environment.
- Historical messages still do not persist citation or memory metadata.
- No custom document preview or citation deep-link target exists yet.
- Formal WCAG certification has not been performed.
- Narrator and NVDA validation remain manual.

## Future Considerations

Future Microsoft integrations and Word add-ins should preserve host-app keyboard conventions, expose clear landmarks/headings, label Office action controls by target document/range where applicable, announce background processing without repeated interruption, avoid exposing secrets or sensitive document content through unnecessary status text, and validate with Narrator, NVDA, and Office keyboard workflows before release.
