# Bootstrap controlado de ADMIN (development)

`aditsystem-bootstrap-admin` aprovisiona exclusivamente la primera cuenta de development `eperez@ervic.pro`. No expone un endpoint HTTP, no genera contraseñas y no modifica cuentas existentes.

Usa el modelo final: crea una `Persona` raíz con `rol=ADMIN` y su `AuthUser` activo en una sola transacción. `AMIGO` nunca recibe credenciales y este comando nunca lo crea.

## Guardas e idempotencia

- Sólo se ejecuta con `APP_ENV=local` o `APP_ENV=development`.
- El único `BOOTSTRAP_EMAIL` autorizado es `eperez@ervic.pro`.
- Si esa cuenta ADMIN activa ya existe, termina con éxito sin cambios.
- Si el correo está asociado a cualquier otra cuenta, incluida `AMIGO`, una cuenta inactiva o eliminada, falla sin alterar registros.
- Si no se configuró el secreto, falla antes de abrir una sesión a la base de datos.

Antes de ejecutarlo en EC2, verifica que la migración que materializa `personas` y `auth_users` del modelo TRA-88 ya se aplicó. Este comando no ejecuta migraciones ni reinicia bases remotas.

## Ejecución controlada

En SSM, entrega el identificador del secreto, no su valor:

```bash
APP_ENV=development \
BOOTSTRAP_EMAIL=eperez@ervic.pro \
BOOTSTRAP_PASSWORD_SECRET_ID=aditsystem/dev/bootstrap-admin \
aditsystem-bootstrap-admin
```

Para local, la contraseña puede proporcionarse únicamente en la sesión controlada:

```bash
APP_ENV=local \
BOOTSTRAP_EMAIL=eperez@ervic.pro \
BOOTSTRAP_PASSWORD='<contraseña no registrada>' \
aditsystem-bootstrap-admin
```

Los atributos no secretos de la persona son opcionales y tienen defaults de development: `BOOTSTRAP_NOMBRE`, `BOOTSTRAP_APELLIDO_PATERNO`, `BOOTSTRAP_APELLIDO_MATERNO` y `BOOTSTRAP_TELEFONO`.

## Verificación y rotación

1. Confirma que el comando devuelve código 0 y que los logs no contienen contraseñas, hashes o tokens.
2. Inicia sesión mediante el flujo de autenticación final con el secreto recuperado por un operador autorizado; confirma que la identidad es `ADMIN`.
3. Rota la contraseña cambiando el valor en Secrets Manager y usando el flujo administrativo final de cambio de contraseña. El bootstrap es deliberadamente inmutable: no actualiza hashes ni roles de cuentas existentes.

## Pruebas

```bash
pytest tests/unit/test_bootstrap_admin.py -v
```
