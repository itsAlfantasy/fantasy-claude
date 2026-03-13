# Development Workflow

## How it works

`install.sh` registers the scripts in `settings.json` using **absolute paths** pointing to your repo directory. This means edits to any existing script are picked up immediately — no reinstall needed.

---

## When you DON'T need to reinstall

Almost always. Changes are live immediately:

| What you changed | Live? | Notes |
|---|---|---|
| Existing element script (`elements/*.sh`) | Yes | Claude Code calls the file directly |
| `statusline/statusline.sh` | Yes | Same |
| `hooks/sounds.sh` or other existing hooks | Yes | Same |
| `config.json` | Yes | Read on every invocation |
| `configure.py` | Yes | Run directly via `configure.sh` |

To test statusline changes locally without a Claude session:

```bash
bash statusline/statusline.sh
```

To test a hook locally:

```bash
echo '{"event": "Stop"}' | bash hooks/sounds.sh
```

---

## When you DO need to reinstall

Run `bash install.sh` only in these cases:

1. **New hook file added** — needs `chmod +x` and possibly registration in `settings.json`
2. **Hook event registration changed** — if you add/remove a `PostToolUse`, `Stop`, or `Notification` entry in `settings.json`
3. **Fresh machine / first install**

For a new element script only, you can skip the full install and just do:

```bash
chmod +x statusline/elements/my-new-element.sh
```

Then add it to `config.json` manually — no `install.sh` needed.

---

## When changes take effect

| Trigger | Picks up changes to... |
|---|---|
| Immediately | `config.json`, any existing `.sh` file |
| New Claude Code session | Hook registrations in `settings.json` |
| Restart Claude Code | Statusline registration changes |

In practice: edit → save → the next statusline tick or hook event will use the new code.

---

## Branch switching

Cambiare branch cambia immediatamente il codice eseguito — al prossimo tick della statusline.

| Scenario | Effetto |
|---|---|
| Branch con script modificato | Usa il nuovo codice subito |
| Branch con un elemento in meno | `config.json` referenzia un `.sh` inesistente → elemento silenzioso o errore |
| Branch con `config.json` diverso | Layout/suoni cambiano subito |
| Branch con nuovo hook non ancora in `settings.json` | L'hook non viene chiamato |

Consiglio: tieni `config.json` stabile tra branch feature, o aggiungi elementi senza rimuovere quelli esistenti per evitare che la statusline si rompa al checkout.

Se un branch cambia struttura pesante (nuovi hook, elementi rinominati), dopo il checkout verifica che `config.json` e gli script siano allineati. Se necessario, riesegui `bash install.sh`.

---

## Development loop (typical)

```
1. Edit file
2. (Optional) bash statusline/statusline.sh  ← quick sanity check
3. Switch to an active Claude session and observe the statusline update
```

No build, no tests, no linter.
