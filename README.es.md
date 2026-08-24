# FastAPI Route Guard

Autorización declarativa a nivel de recurso para FastAPI.

> **Resumen en español.** La referencia completa —handlers personalizados,
> modelo de seguridad, comportamiento de errores— está en el
> [README en inglés](https://github.com/erick9125/fastapi-route-guard/blob/main/README.md), que es la documentación que se mantiene al
> día. Esta página cubre lo justo para entender el paquete y arrancar.

## El problema

FastAPI puede autenticar a un usuario y verificar scopes. Eso no responde:

> ¿Puede _este_ principal leer _esta_ factura?

`GET /invoices/123` funciona para cualquiera que tenga `invoice:read`, incluso
si la factura pertenece a otro tenant o a otro dueño. Es la clase de fallo que
OWASP llama BOLA / IDOR: el endpoint está autorizado, el objeto no.

## Qué resuelve

Evalúa, en una sola decisión: principal autenticado, acción, recurso,
pertenencia (`ownership`), tenant, roles, scopes y policies personalizadas.

- `RouteGuard` y `Depends`, idiomático en FastAPI
- deny por defecto, fail-closed
- `403` genérico, sin filtrar códigos internos ni ids de tenant o dueño
- el guard carga el recurso y el endpoint recibe el mismo objeto
- un evaluador sin dependencia de FastAPI, testeable en aislamiento

No es un IAM: no emite JWTs, no autentica, no reemplaza tu dependency de
identidad. La autenticación tiene que ocurrir **antes** de `RouteGuard`.

## Instalación

```bash
pip install fastapi-route-guard
```

Requiere Python 3.11+ y FastAPI.

## Uso mínimo

```python
from fastapi import Depends
from fastapi_route_guard import RouteGuard

guard = RouteGuard(principal=current_principal)
guard.add_resource(
    "invoice",
    resolver=resolve_invoice,
    attributes=invoice_attributes,
)


@app.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice: Invoice = Depends(
        guard.protect_resource(
            "invoice",
            id_param="invoice_id",
            scopes={"invoice:read"},
            tenant=True,
        )
    ),
):
    return invoice
```

`user-a` leyendo `invoice-a` → `200`. El mismo usuario cambiando el id a
`invoice-b` (otro tenant) → `403`.

## Licencia

MIT.
