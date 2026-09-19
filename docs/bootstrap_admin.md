# Bootstrap: primer administrador

Procedimiento para crear la primera cuenta `ADMIN` en el entorno de desarrollo.

## Descripción general

`aditsystem-bootstrap-admin` es un comando CLI idempotente, sin HTTP, que ejecuta el aprovisionamiento inicial. No crea ni amplía endpoints públicos; `POST /auth/register` continúa limitado a rol `INVITADO`.

### Contrato de idempotencia

| Estado del correo en la BD | Resultado |
|---|---|
| No existe | Crea cuenta `ADMIN` → exit 0 |
| Existe con rol `ADMIN` | Sin cambios → exit 0 |
| Existe con otro rol | Error explícito → exit 1 |

Nunca escribe la contraseña, el hash ni ningún token en los logs.

---

## Ejecución mediante SSM (producción / desarrollo en EC2)

### Requisitos previos

1. El secreto ya existe en AWS Secrets Manager: `aditsystem/dev/admin-password`
   - Valor: contraseña en texto plano (≥ 8 caracteres).
2. La instancia EC2 tiene permiso IAM `secretsmanager:GetSecretValue` para ese ARN.
3. El paquete `boto3` está instalado (`pip install aditsystem-backend[aws]`).

### Comando SSM

```bash
aws ssm send-command \
  --instance-ids "i-0123456789abcdef0" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "cd /opt/aditsystem",
    "BOOTSTRAP_EMAIL=eperez@ervic.pro \
     BOOTSTRAP_NAME=\"Ervic Perez\" \
     BOOTSTRAP_PASSWORD_SECRET_ID=aditsystem/dev/admin-password \
     aditsystem-bootstrap-admin"
  ]' \
  --output text \
  --query "Command.CommandId"
```

Consulta el resultado:

```bash
aws ssm get-command-invocation \
  --command-id "<CommandId>" \
  --instance-id "i-0123456789abcdef0" \
  --query "[Status,StandardOutputContent,StandardErrorContent]"
```

Salida esperada en éxito:

```
INFO ADMIN user 'eperez@ervic.pro' created successfully.
```

---

## Verificación

Confirma la cuenta con una llamada al endpoint de login:

```bash
curl -X POST https://api.aditsystem.ervic.pro/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"eperez@ervic.pro","password":"<contraseña>"}'
```

La respuesta debe incluir `"role":"ADMIN"` en el payload del token.

---

## Rotación de contraseña

1. Actualiza el secreto en Secrets Manager con la nueva contraseña.
2. Inicia sesión como `ADMIN` en la API.
3. Usa `PATCH /api/v1/admin/users/{id}` para cambiar la contraseña de la cuenta.
4. El comando bootstrap **no modifica** cuentas existentes; la rotación es una operación de la API.

---

## Variables de entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `BOOTSTRAP_EMAIL` | Sí | Correo de la cuenta administradora |
| `BOOTSTRAP_NAME` | No | Nombre completo (default: `Administrador`) |
| `BOOTSTRAP_PASSWORD_SECRET_ID` | Recomendado en EC2/SSM | ID del secreto en AWS Secrets Manager |
| `BOOTSTRAP_PASSWORD` | Solo local/dev | Contraseña en texto plano (no usar en producción) |
| `DATABASE_URL` | Sí (vía settings) | URL PostgreSQL async |

---

## Ejecución local (desarrollo)

```bash
# Desde la raíz del repositorio
BOOTSTRAP_EMAIL=dev-admin@example.com \
BOOTSTRAP_PASSWORD=dev-only-password \
python scripts/create_superuser.py
```

O con el comando instalado:

```bash
pip install -e ".[aws]"
BOOTSTRAP_EMAIL=dev-admin@example.com \
BOOTSTRAP_PASSWORD=dev-only-password \
aditsystem-bootstrap-admin
```

---

## Pruebas

```bash
pytest tests/unit/test_bootstrap_admin.py -v
```

Cobertura de los casos: creación, repetición (idempotencia), conflicto de rol y secreto no configurado.
