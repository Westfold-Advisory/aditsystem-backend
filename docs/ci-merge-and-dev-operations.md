# CI, auto-merge y operaciones en development

## Política de merge (2026-09)

- **0 reviews** humanas requeridas por ahora.
- **Squash merge** vía auto-merge cuando los **required checks** del PR estén verdes.
- Secret **`AUTOMERGE_PAT`**: PAT o GitHub App token del bot/agente con `contents:write` y
  `pull_requests:write` (ya configurado en el org).

### Branch protection observada (GitHub API)

| Repo | Required checks | Required reviews |
|------|-----------------|------------------|
| `ADITSYSTEM` | `Quality gates`, `Semgrep SAST` (strict) | No configurado en API clásica |
| `aditsystem-backend` | **Ninguno** en regla clásica actual | No |

**Acción recomendada (backend):** en `main`, marcar como required los jobs de **Backend CI**:

- `Lint and test`
- `Integration tests (Postgres)`
- `Build and scan image`

Activar **Allow auto-merge** en Settings → General → Pull Requests (ambos repos).

## Flujo de pipelines

### Backend

| Evento | Workflow | Qué corre |
|--------|----------|-----------|
| Pull request → `main` | `Backend CI` | lint, unit, integration, build+Trivy (sin push) |
| Push → `main` | `Backend release` | build+Trivy+push ECR, deploy SSM |
| PR abierto/actualizado | `Enable PR auto-merge` | activa auto-merge squash |

Evita duplicar pytest/integration en push a `main`: la calidad se valida en el PR; el merge
dispara solo **release**.

### Frontend

| Evento | Workflow |
|--------|----------|
| PR / push `main` | `Frontend CI/CD` (ver optimización futura en issue de infra) |
| PR | `Enable PR auto-merge` (repo ADITSYSTEM) |

## Dispatchers manuales (sin pegar en SSM)

Todos usan OIDC + `environment: development` + instancia `AWS_EC2_INSTANCE_ID`.

| Workflow | Confirmación | Uso |
|----------|--------------|-----|
| Development database reset | `RESET_DEVELOPMENT_DATA` | Borrado schema + migrate |
| Development seed Faker hierarchy | `SEED_DEVELOPMENT_FAKER` | Jerarquía ficticia |
| Development bootstrap admin | `BOOTSTRAP_DEVELOPMENT_ADMIN` | Primer ADMIN `eperez@ervic.pro` |
| Development seed team admins | `SEED_DEVELOPMENT_TEAM_ADMINS` | Admins de equipo vía secret emails |

Inputs comunes: **`change_id`** (auditoría).

### Secrets / vars AWS

- `TEAM_ADMIN_EMAILS_SECRET_ID` (opcional en SM): JSON `{"emails":"a@b.com,c@d.com"}`
- Default en script: `aditsystem-dev/team-admin-emails`, `aditsystem-dev/bootstrap-admin`

Los wrappers SSM en EC2 esperan scripts en `/opt/aditsystem/*.sh` (provisionados con la AMI
/ runbook de infra).

## Operaciones aún destructivas

Reset de DB mantiene confirmación literal y environment protegido. No auto-merge en workflows
de reset/faker.
