# Distribution Plan

Piano per versionamento, release e distribuzione di fantasy-claude.

---

## 1. Versioning (Semantic Versioning)

Schema: `MAJOR.MINOR.PATCH`

| Livello | Quando incrementare | Esempio |
|---------|-------------------|---------|
| **MAJOR** | Breaking changes al formato `config.json`, rimozione elementi, cambio comportamento install | `2.0.0` |
| **MINOR** | Nuovi elementi statusline, nuovi hooks, feature TUI, nuovi suoni | `1.3.0` |
| **PATCH** | Bug fix, miglioramenti script, docs | `1.3.1` |

**Versione iniziale:** `1.0.0` -- il progetto ha gia un feature set stabile (18+ elementi, TUI, sound hooks).

**Dove salvare la versione:** un file `VERSION` alla root della repo con solo il numero (es. `1.0.0`). Semplice, leggibile da bash e Python.

---

## 2. GitHub Releases

### Procedura per ogni release

```bash
# 1. Aggiorna VERSION e CHANGELOG.md
echo "1.0.0" > VERSION
# Scrivi le note in CHANGELOG.md

# 2. Commit e tag
git add VERSION CHANGELOG.md
git commit -m "Release 1.0.0"
git tag v1.0.0
git push origin main --tags

# 3. Crea la release su GitHub
gh release create v1.0.0 --title "v1.0.0" --notes-file CHANGELOG.md
```

GitHub genera automaticamente il tarball `.tar.gz` e `.zip` per ogni tag. Non servono artifact compilati.

### Automazione

Il workflow `.github/workflows/release.yml` gestisce tutto al push di un tag `v*`: aggiorna `VERSION` e `package.json`, crea la GitHub Release, pubblica su npm.

**Prerequisito:** aggiungere il secret `NPM_TOKEN` in Settings → Secrets della repo GitHub. Il token si genera su npmjs.com → Access Tokens → Automation.

---

## 3. Canali di Distribuzione

### Priorita consigliata

1. **GitHub Releases** -- fondazione per tutto il resto
2. **`curl | bash` installer** -- minimo sforzo, massimo risultato
3. **npm** -- naturale per utenti Claude Code (che hanno gia Node.js)

---

### 3a. Curl | Bash (one-liner)

Il modo piu semplice. Crei uno script `install-remote.sh` nella repo:

```bash
#!/bin/bash
set -e
INSTALL_DIR="$HOME/.fantasy-claude"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating fantasy-claude..."
    git -C "$INSTALL_DIR" pull origin main
else
    echo "Installing fantasy-claude..."
    git clone https://github.com/itsAlfantasy/fantasy-claude.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
bash install.sh
echo "Done! Restart Claude Code to apply changes."
```

**L'utente installa con:**
```bash
curl -fsSL https://raw.githubusercontent.com/itsAlfantasy/fantasy-claude/main/install-remote.sh | bash
```

Pro: zero infrastruttura, funziona subito, supporta anche update.

---

### 3b. npm

Claude Code e un'app Node.js, quindi gli utenti hanno gia `npm`. E il canale piu naturale.

**Cosa serve:**

1. Un `package.json`:
```json
{
  "name": "fantasy-claude",
  "version": "1.0.0",
  "description": "Statusline and sound hooks for Claude Code",
  "bin": {
    "fantasy-claude": "./cli.sh",
    "fanclaude": "./cli.sh"
  },
  "files": [
    "statusline/",
    "hooks/",
    "sounds/",
    "config.json",
    "configure.py",
    "configure.sh",
    "install.sh",
    "cli.sh",
    "VERSION"
  ],
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/itsAlfantasy/fantasy-claude"
  }
}
```

2. Un `cli.sh` come entry point:
```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  install)   exec bash "$SCRIPT_DIR/install.sh" ;;
  --version) cat "$SCRIPT_DIR/VERSION" ;;
  *)         exec bash "$SCRIPT_DIR/configure.sh" ;;
esac
```

Senza argomenti apre direttamente il TUI. `install` e `--version` restano come escape hatch.

**L'utente installa con:**
```bash
npm install -g fantasy-claude
fanclaude  # auto-setup + apre il TUI
```

Al primo avvio, `configure.py` detecta se `settings.json` e gia configurato. Se non lo e, patcha automaticamente prima di mostrare il TUI. Zero comandi extra, zero sorprese: l'utente vede il setup solo quando apre il configurator.

**Per pubblicare:** vedi il workflow di release in sezione 6. La CI gestisce tutto al push del tag.

**Nota sul nome:** `fantasy-claude` potrebbe essere gia preso su npm. Verificare con `npm view fantasy-claude`. Il pacchetto espone due comandi: `fantasy-claude` (nome completo) e `fanclaude` (abbreviazione).

---

## 4. File da Creare/Modificare

| File | Azione | Scopo |
|------|--------|-------|
| `VERSION` | Creare | Contiene solo `1.0.0` |
| `LICENSE` | Creare | Licenza MIT -- **obbligatorio** per npm |
| `CHANGELOG.md` | Creare | Note di rilascio per ogni versione |
| `package.json` | Creare | Metadata per npm |
| `cli.sh` | Creare | Entry point CLI per npm |
| `install-remote.sh` | Creare | Script per `curl \| bash` |
| `.github/workflows/release.yml` | Creare | Automazione release |
| `.gitignore` | Modificare | Aggiungere `node_modules/` |
| `install.sh` | Modificare | Leggere e mostrare versione da `VERSION` |
| `configure.py` | Modificare | Mostrare versione nel TUI header |
| `README.md` | Modificare | Istruzioni install per tutti i canali |

---

## 5. Prerequisiti

Prima di qualsiasi distribuzione:

1. **Aggiungi `LICENSE`** -- senza licenza il software non e tecnicamente open source. MIT e la scelta standard per tool CLI. Vai su GitHub > repo > Add file > "LICENSE" e scegli MIT, oppure crealo manualmente.

2. **Verifica il nome su npm:** `npm view fantasy-claude` -- se esiste, usa un nome alternativo.

3. **Crea account npmjs.com** se non ne hai uno.

---

## 6. Workflow di Release

Il developer fa solo due cose — il resto e automatico:

```
1. Sviluppa su branch feature → merge su main
2. Aggiorna CHANGELOG.md con le note della release
3. git add CHANGELOG.md && git commit -m "Release X.Y.Z"
4. git tag vX.Y.Z && git push origin main --tags
   → GitHub Action aggiorna VERSION + package.json, crea la release, pubblica su npm
```

`VERSION` e `package.json` vengono aggiornati dalla CI, non manualmente.

---

## 7. Meccanismo di Update

Per utenti che hanno installato via git clone:

```bash
# Aggiungi a install.sh un flag "update"
fantasy-claude update
# oppure
cd ~/.fantasy-claude && git pull && bash install.sh
```

Per npm: `npm update -g fantasy-claude`
