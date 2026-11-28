# What works where

Check this before saying something can't be done, and update it when a route
is proven or fails. Dates are when a route was last verified.

| Need | Route | Status | Verified |
|---|---|---|---|
| iFUNDS fund data | Cloud shell or cloud browser | ❌ Manulife (Akamai) returns 403 to data-centre IPs | 26 Nov 2026 |
| iFUNDS fund data | Built-in browser on the PC (Cowork, or a Claude Code session on the PC) | ✅ | 26 Nov 2026 |
| Start a session on the PC from a cloud session | `create_session` on the bridge environment "ChadMachine … Claude Bridge" | ✅ once the cloud session is approved for trusted devices (one card per session) | 26 Nov 2026 |
| Link a PC folder into a cloud session | `request_computer_folder` | ❌ ChadMachine doesn't offer folders to cloud sessions (Windows app); cause unconfirmed | 26 Nov 2026 |
| Start a PC session from an artifact page | `Claude Code Remote` connector via the page's `mcp` capability | ❌ tools blocked for pages on this account | 26 Nov 2026 |
| Ask Claude from an artifact page | `comments.sendToClaude` (the Desk's "Fetch on my PC") | Built; needs a trusted session watching the Desk; end-to-end not yet confirmed | 26 Nov 2026 |
| PC session tools | Built-in browser, manulife-ifunds-fund-data skill, Google Drive, ArtifactData | ✅ (checked by a PC session) | 26 Nov 2026 |
| PC sessions run unattended | Sessions started remotely stop at permission prompts (e.g. Glob) until approved on the PC | ⚠️ start them with `permission_mode: "auto"` and check status after starting | 26 Nov 2026 |
| Google Sheets from a page | `mcp` capability, `Google Sheets` / `get_values` | ✅ (Desk, Production 2026) | 26 Nov 2026 |
| Upload account skills | claude.ai Customize → Skills → + → Create skill → Upload; description ≤ 200 characters | ✅ | 26 Nov 2026 |
| Run Python on the PC | Claude Code session on ChadMachine | ❌ no Python installed (only the Windows Store stub); processing runs in the cloud instead | 26 Nov 2026 |
