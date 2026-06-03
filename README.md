# ADITSYSTEM — Backend

API y lógica de servidor del proyecto **ADITSYSTEM**, construido con [Next.js](https://nextjs.org) (App Router) y TypeScript.

- Frontend: https://github.com/Arcoexplsoivo1/ADITSYSTEM
- Infraestructura (Terraform): https://github.com/ervicperezdev/aditsystem-infrastructure

## Requisitos

- Node.js 20 LTS o superior
- npm 10+

## Desarrollo local

```bash
npm install
npm run dev
```

Abre http://localhost:3000

## Scripts

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Servidor de desarrollo |
| `npm run build` | Build de producción |
| `npm run start` | Servidor en modo producción |
| `npm run lint` | ESLint |

## Estrategia de ramas

- `main` — producción (protegida; solo merges vía PR)
- `feature/<nombre>` — desarrollo; PR hacia `main`

El pipeline de CI/CD se configurará en una tarea posterior (TRA-49).

## Estructura

```
src/
  app/          # App Router (páginas y API routes)
public/         # Assets estáticos
```
