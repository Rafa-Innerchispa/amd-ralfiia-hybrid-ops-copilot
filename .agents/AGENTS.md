# Project Customization Rules — RalfIIA Hybrid Ops Copilot

## 📋 Multi-Agent Alignment & Outbox Protocol
To prevent architecture discrepancies, duplicate tasks, or port mismatches across the multi-agent mesh, the active agent MUST follow this protocol upon start:

1. **Scan Coordination Outboxes**:
   Before making any code edits, database schema updates, or routing decisions, read the latest `OUTBOX.md` logs of all active developer agents under the coordination directory `/home/rlopez/data/ai_coordination/`:
   - [ChatGPT Outbox](file:///home/rlopez/data/ai_coordination/chatgpt/OUTBOX.md)
   - [Codex Outbox](file:///home/rlopez/data/ai_coordination/codex/OUTBOX.md)
   - [Cursor Outbox](file:///home/rlopez/data/ai_coordination/cursor/OUTBOX.md)
   - [Antigravity Outbox](file:///home/rlopez/data/ai_coordination/antigravity/OUTBOX.md)

2. **Deduplicate Database Schemes**:
   When working with the PC Doctor field operations store, always use unique compound indexes (`dedupe_key`) and normalization functions (`phone_digits`, `email_norm`, `site_code_norm`, `serial_digits`, `asset_tag_norm`) defined in `pcdoctor_store.py` to prevent duplicate document insertion.

3. **Port & Gateway Integrity**:
   - Upstream services must map to their canonical ports defined in `/home/rlopez/data/ai_coordination/PORTS_CANONICAL.md`.
   - Never modify ngrok tunnels, port definitions, or Docker parameters without checking if it conflicts with other agents' local services.
