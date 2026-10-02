---
title: Warum ich diesen Blog starte
date: 2026-10-03
tags: [meta, agile]
description: Worüber ich hier schreibe und wie die Seite mit Markdown, einer POSIX-Shell und pandoc gebaut ist.
---

Hier schreibe ich über **agile Softwareentwicklung**, **AI**, **Angular** und das Handwerk als **Scrum Master**.

## Wie die Seite gebaut ist

Jeder Beitrag ist eine Markdown-Datei. Ein kleines POSIX-Shellskript wandelt sie mit
[pandoc](https://pandoc.org) in HTML um, und eine GitHub Action veröffentlicht das Ergebnis
auf GitHub Pages:

```sh
git add posts/2026-10-03-warum-dieser-blog.md
git commit -m "Neuer Post"
git push   # den Rest erledigt GitHub
```

Kein Framework, keine `node_modules`, nur Text.
