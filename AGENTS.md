## Agent skills

### Issue tracker

GitHub Issues via `gh` (comcy/comcy.github.io); external PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Flow labels

Second label dimension (`status:*`) for the agile flow, not handled by the skills. See `docs/agents/flow-labels.md`.

### Domain docs

Single-context. See `docs/agents/domain.md`.

## Commits

Conventional Commits (`type(scope): Betreff`, erzwungen durch Hook `commit-msg` und CI-Job `gates`). Autor der Commits: `christian.silfang@gmail.com` (`git -c user.email=… commit` oder `git config user.email`). Vor dem Commit prüft der Hook `pre-commit` auf Secrets; ein Treffer wird behoben, nicht umgangen. Details: `docs/workflow.md`.

## Bauen

Fehlerbehebung und neue Funktion mit **rotem Test zuerst** (Skill `tdd`, Teil von `/implement`): erst ein Test, der den Fehler zeigt, dann die Änderung, dann alles grün. Der Test liegt an der äußeren Naht (Aufruf des Programms), nicht an inneren Funktionen. Kein `git stash`, solange mehrere Worktrees parallel genutzt werden.
