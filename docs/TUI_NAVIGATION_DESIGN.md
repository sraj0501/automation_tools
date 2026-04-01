# TUI Navigation Design

> **Architecture decision document.** Defines the universal navigation contract for all DevTrack TUI flows. All new interactive prompts must follow this design.

**Status**: Planned — not yet implemented
**Last reviewed**: April 1, 2026

---

## The Rule

> **ESC = go back one step. Ctrl+C = cancel the entire flow.**

This applies to every interactive prompt in DevTrack without exception. No prompt should silently exit or cancel the flow when ESC is pressed — it should return the user to the previous step.

---

## Why the Current Behaviour Is Wrong

The current TUI (`backend/user_prompt.py`) uses Python's `input()` — line-buffered, never sees individual keypresses. ESC triggers terminal-dependent behaviour that typically cancels the prompt entirely. There is also no concept of a "previous step" in the architecture; each prompt is a standalone call with no memory of what came before.

---

## The Navigation Contract

| Key | Action | Behaviour |
|---|---|---|
| `ESC` | Back | Return to previous step. If already on first step: stay, show "Already at the start. Ctrl+C to cancel." |
| `Ctrl+C` | Cancel | Abort the entire flow immediately. Show "Cancelled." |
| `Enter` | Forward | Accept current input and advance to next step |
| `↑ ↓` | Navigate | Move selection within a list (ticket picker, choice prompt) |
| `e` / `Tab` | Edit | Open edit mode for a pre-filled field (where supported) |

---

## Architecture Changes

### `StepResult` — return type for all flow steps

```python
@dataclass
class StepResult:
    action: Literal["forward", "back", "cancel"]
    data: Any = None   # populated only when action="forward"
```

### `UserResponse` — backward-compatible addition

```python
@dataclass
class UserResponse:
    raw_input: str
    timestamp: datetime
    timed_out: bool = False
    cancelled: bool = False   # Ctrl+C — unchanged meaning
    went_back: bool = False   # ESC  — new field
```

Existing callers that don't check `went_back` are unaffected.

### `RawInput` — raw terminal keypress detection

Replaces `input()` and `sys.stdin.readline()` everywhere user input is read.

```
Behaviour in raw terminal mode (termios.setraw):

  \x03          →  Ctrl+C  →  StepResult("cancel")
  \x1b          →  ESC     →  StepResult("back")
                   (distinguished from arrow keys by 50ms timeout on next byte)
  \x1b[A/B/C/D  →  Arrow keys — navigation within the current step
  \r or \n      →  Enter   →  StepResult("forward", accumulated_text)
  \x7f / \x08   →  Backspace — remove last char from buffer
  printable     →  Append to line buffer, echo to terminal

Terminal is always restored on exception (try/finally).
Windows fallback: line-buffered input(), no raw mode.
```

### `FlowController` — multi-step flow orchestrator

```python
class FlowController:
    def __init__(self, steps: list[Callable[[dict], StepResult]]):
        self.steps = steps

    def run(self) -> dict | None:
        """
        Runs steps in sequence.
        Returns accumulated results dict on completion.
        Returns None if user cancels (Ctrl+C).
        """
```

**Navigation logic**:
- `forward` → store result, advance to next step
- `back` on step 0 → show hint, re-run step 0
- `back` on step N > 0 → clear step N result, go to step N-1
- `cancel` → print "Cancelled.", return None

---

## Example: Commit Approval Flow

```python
def run_commit_approval(context: CommitContext) -> dict | None:
    return FlowController([
        lambda r: step_commit_message(context, r),   # Step 0
        lambda r: step_ticket_selection(context, r),  # Step 1
        lambda r: step_pm_update(context, r),         # Step 2
        lambda r: step_confirm(context, r),            # Step 3
    ]).run()
```

ESC on step 2 (PM update) → back to step 1 (ticket selection) → back to step 0 (commit message) → "Already at the start. Ctrl+C to cancel."

---

## Files to Change

| File | Change |
|---|---|
| `backend/user_prompt.py` | Add `StepResult`, `RawInput`, `FlowController`; add `went_back` to `UserResponse`; swap `input()` for `RawInput.readline()` in `_prompt_simple` and `_prompt_with_timeout` |
| `backend/git_sage/cli.py` | Update approval dialog to use `FlowController` |

All future multi-step TUI flows must use `FlowController` from the start.

---

---

## See Also

- Anonymous ping design (uniqueness + anti-inflation): [project_anon_ping.md](../memory/project_anon_ping.md) — covers UUID + fingerprint approach

---

## Non-Interactive Mode (CI / Tests)

Raw input is bypassed entirely in non-interactive mode (`not sys.stdin.isatty()`). Behaviour is unchanged: `DEVTRACK_INPUT` env var provides input, or defaults are used. `went_back` is always `False` in non-interactive mode.
