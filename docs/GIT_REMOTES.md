# Git remotes — GitHub + GitLab

## GitHub (principal)

- **Repo:** https://github.com/Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot
- **Remote:** `origin`
- **Branch:** `main`

```bash
git push origin main
```

## GitLab (mirror manual)

El repo **no existe aún** en GitLab (`rafagye/amd-ralfiia-hybrid-ops-copilot` → 404).

Pasos en el servidor (después de crear el proyecto vacío en gitlab.com):

```bash
cd /home/rlopez/projects/amd-ralfiia-hybrid-ops-copilot
git remote add gitlab https://gitlab.com/rafagye/amd-ralfiia-hybrid-ops-copilot.git
git push -u gitlab main
```

Usar **Personal Access Token** o SSH key — no pegar tokens en la URL del remote (usar `git credential` o `glab auth login`).

## Secretos — NUNCA subir

| Archivo | Estado |
|---------|--------|
| `.env` | **gitignored** — solo en servidor |
| `.env.example` | Placeholders vacíos — OK en git |
| `FIREWORKS_API_KEY`, `AMD_CLOUD_API_TOKEN` | Solo en `.env` local |

Verificar antes de push:

```bash
git check-ignore -v .env   # debe mostrar .gitignore
git status                 # .env NO debe aparecer
```
