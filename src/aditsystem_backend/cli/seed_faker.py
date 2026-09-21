"""Mass-generate fictional hierarchy trees for local development and QA.

Creates COORDINADOR_GENERAL → COORDINADOR → ENLACE → AMIGO subtrees with
Mexican-locale Faker data. Authenticatable roles receive ``auth_users`` rows;
AMIGO personas never do. Not available outside local/development ``APP_ENV``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from faker import Faker
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from aditsystem_backend.cli.bootstrap_admin import BootstrapError, resolve_password
from aditsystem_backend.core.config import get_settings
from aditsystem_backend.core.security import hash_password
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.documento import Documento
from aditsystem_backend.models.enums import (
    AUTHENTICABLE_PERSON_ROLES,
    DocumentoTipo,
    PersonRole,
)
from aditsystem_backend.models.persona import Persona

logger = logging.getLogger(__name__)
ALLOWED_ENVIRONMENTS = frozenset({"local", "development"})
DEFAULT_DOMAIN = "aditsystem.test"
EMAIL_MARKER = "faker"
ROLE_SLUG = {
    PersonRole.COORDINADOR_GENERAL: "cg",
    PersonRole.COORDINADOR: "co",
    PersonRole.ENLACE: "en",
}


@dataclass(frozen=True)
class SeedFakerConfig:
    coordinadores_generales: int = 2
    coordinadores_por_cg: int = 3
    enlaces_por_coordinador: int = 5
    amigos_por_enlace: int = 10
    email_domain: str = DEFAULT_DOMAIN
    faker_seed: int = 42_120
    document_storage_dir: Path = Path("demo-document-storage")


@dataclass(frozen=True)
class PlannedPerson:
    role: PersonRole
    email: str | None
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    telefono: str
    latitud: Decimal
    longitud: Decimal
    cg_index: int
    co_index: int | None
    en_index: int | None
    am_index: int | None


@dataclass(frozen=True)
class SeedAccountExport:
    email: str | None
    rol: str
    persona_id: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "email": self.email,
            "rol": self.rol,
            "persona_id": self.persona_id,
        }


def _validate_runtime() -> None:
    environment = get_settings().app_env.strip().lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise BootstrapError(
            "El seed Faker sólo se permite con APP_ENV local o development."
        )


def _role_email(
    role: PersonRole,
    *,
    domain: str,
    cg_index: int,
    co_index: int | None = None,
    en_index: int | None = None,
) -> str:
    slug = ROLE_SLUG[role]
    parts = [EMAIL_MARKER, slug, str(cg_index)]
    if co_index is not None:
        parts.append(str(co_index))
    if en_index is not None:
        parts.append(str(en_index))
    return f"{'.'.join(parts)}@{domain}"


def _amigo_telefono(cg_index: int, co_index: int, en_index: int, am_index: int) -> str:
    """Reserved 55599* prefix marks Faker AMIGO rows for fresh-subtree cleanup."""
    return f"55599{cg_index:02d}{co_index:02d}{en_index:02d}{am_index:04d}"


def _person_name(fake: Faker) -> tuple[str, str, str]:
    first = fake.first_name()
    last = fake.last_name()
    maternal = fake.last_name()
    return first, last, maternal


def _phone(fake: Faker) -> str:
    digits = fake.numerify("##########")
    return f"555{digits[:7]}"


def _coordinates(
    cg_index: int,
    co_index: int | None,
    en_index: int | None,
    am_index: int | None,
) -> tuple[Decimal, Decimal]:
    """Return stable, varied points around Puebla districts for map QA.

    Coordinates intentionally use small deterministic offsets rather than a
    geocoding service, so the seed is reproducible and works offline.
    """
    district_centres = (
        (Decimal("19.043300"), Decimal("-98.201900")),  # Puebla centro
        (Decimal("18.461500"), Decimal("-97.392000")),  # Tehuacán
        (Decimal("19.198000"), Decimal("-98.048000")),  # Amozoc
        (Decimal("19.061000"), Decimal("-98.307000")),  # San Pedro Cholula
    )
    base_lat, base_lng = district_centres[cg_index % len(district_centres)]
    sequence = (co_index or 0) * 31 + (en_index or 0) * 7 + (am_index or 0)
    return (
        base_lat + Decimal((sequence % 9) - 4) / Decimal("1000"),
        base_lng + Decimal(((sequence // 3) % 9) - 4) / Decimal("1000"),
    )


def iter_planned_people(config: SeedFakerConfig) -> Iterator[PlannedPerson]:
    """Pure hierarchy planner (deterministic when ``config.faker_seed`` is fixed)."""
    fake = Faker("es_MX")
    fake.seed_instance(config.faker_seed)
    for cg_index in range(config.coordinadores_generales):
        nombre, ap_pat, ap_mat = _person_name(fake)
        latitud, longitud = _coordinates(cg_index, None, None, None)
        yield PlannedPerson(
            role=PersonRole.COORDINADOR_GENERAL,
            email=_role_email(
                PersonRole.COORDINADOR_GENERAL,
                domain=config.email_domain,
                cg_index=cg_index,
            ),
            nombre=nombre,
            apellido_paterno=ap_pat,
            apellido_materno=ap_mat,
            telefono=_phone(fake),
            latitud=latitud,
            longitud=longitud,
            cg_index=cg_index,
            co_index=None,
            en_index=None,
            am_index=None,
        )
        for co_index in range(config.coordinadores_por_cg):
            nombre, ap_pat, ap_mat = _person_name(fake)
            latitud, longitud = _coordinates(cg_index, co_index, None, None)
            yield PlannedPerson(
                role=PersonRole.COORDINADOR,
                email=_role_email(
                    PersonRole.COORDINADOR,
                    domain=config.email_domain,
                    cg_index=cg_index,
                    co_index=co_index,
                ),
                nombre=nombre,
                apellido_paterno=ap_pat,
                apellido_materno=ap_mat,
                telefono=_phone(fake),
                latitud=latitud,
                longitud=longitud,
                cg_index=cg_index,
                co_index=co_index,
                en_index=None,
                am_index=None,
            )
            for en_index in range(config.enlaces_por_coordinador):
                nombre, ap_pat, ap_mat = _person_name(fake)
                latitud, longitud = _coordinates(cg_index, co_index, en_index, None)
                yield PlannedPerson(
                    role=PersonRole.ENLACE,
                    email=_role_email(
                        PersonRole.ENLACE,
                        domain=config.email_domain,
                        cg_index=cg_index,
                        co_index=co_index,
                        en_index=en_index,
                    ),
                    nombre=nombre,
                    apellido_paterno=ap_pat,
                    apellido_materno=ap_mat,
                    telefono=_phone(fake),
                    latitud=latitud,
                    longitud=longitud,
                    cg_index=cg_index,
                    co_index=co_index,
                    en_index=en_index,
                    am_index=None,
                )
                for am_index in range(config.amigos_por_enlace):
                    nombre, ap_pat, ap_mat = _person_name(fake)
                    latitud, longitud = _coordinates(
                        cg_index, co_index, en_index, am_index
                    )
                    yield PlannedPerson(
                        role=PersonRole.AMIGO,
                        email=None,
                        nombre=nombre,
                        apellido_paterno=ap_pat,
                        apellido_materno=ap_mat,
                        telefono=_amigo_telefono(
                            cg_index, co_index, en_index, am_index
                        ),
                        latitud=latitud,
                        longitud=longitud,
                        cg_index=cg_index,
                        co_index=co_index,
                        en_index=en_index,
                        am_index=am_index,
                    )


def count_planned_people(config: SeedFakerConfig) -> int:
    per_cg = 1 + config.coordinadores_por_cg * (
        1 + config.enlaces_por_coordinador * (1 + config.amigos_por_enlace)
    )
    return config.coordinadores_generales * per_cg


def _parent_key(plan: PlannedPerson) -> tuple[int, int | None, int | None] | None:
    if plan.role is PersonRole.COORDINADOR_GENERAL:
        return None
    if plan.role is PersonRole.COORDINADOR:
        return (plan.cg_index, None, None)
    if plan.role is PersonRole.ENLACE:
        return (plan.cg_index, plan.co_index, None)
    return (plan.cg_index, plan.co_index, plan.en_index)


def _node_key(plan: PlannedPerson) -> tuple[int, int | None, int | None]:
    return (plan.cg_index, plan.co_index, plan.en_index)


async def _find_user_by_email(session: AsyncSession, email: str) -> AuthUser | None:
    result = await session.execute(
        select(AuthUser).where(func.lower(AuthUser.email) == email.lower())
    )
    return result.scalar_one_or_none()


async def _find_amigo_by_telefono(
    session: AsyncSession, telefono: str
) -> Persona | None:
    result = await session.execute(
        select(Persona).where(
            Persona.rol == PersonRole.AMIGO,
            Persona.telefono == telefono,
        )
    )
    return result.scalar_one_or_none()


async def _collect_faker_subtree_persona_ids(
    session: AsyncSession, domain: str
) -> set[str]:
    pattern = f"{EMAIL_MARKER}.cg.%@{domain.lower()}"
    roots = await session.execute(
        select(Persona.id)
        .join(AuthUser, AuthUser.persona_id == Persona.id)
        .where(
            Persona.rol == PersonRole.COORDINADOR_GENERAL,
            func.lower(AuthUser.email).like(pattern),
        )
    )
    root_ids = list(roots.scalars())
    if not root_ids:
        orphan_amigos = await session.execute(
            select(Persona.id).where(
                Persona.rol == PersonRole.AMIGO,
                Persona.telefono.like("55599%"),
            )
        )
        return set(orphan_amigos.scalars())

    lineage = (
        select(Persona.id, Persona.parent_persona_id)
        .where(Persona.id.in_(root_ids))
        .cte("faker_lineage", recursive=True)
    )
    parent = Persona.__table__.alias("faker_parent")
    lineage = lineage.union_all(
        select(parent.c.id, parent.c.parent_persona_id).join(
            lineage, parent.c.parent_persona_id == lineage.c.id
        )
    )
    descendants = await session.execute(select(lineage.c.id))
    return set(descendants.scalars())


async def delete_faker_subtrees(session: AsyncSession, *, email_domain: str) -> int:
    persona_ids = await _collect_faker_subtree_persona_ids(session, email_domain)
    if not persona_ids:
        return 0
    await session.execute(
        delete(Documento).where(Documento.persona_id.in_(persona_ids))
    )
    await session.execute(delete(AuthUser).where(AuthUser.persona_id.in_(persona_ids)))
    result = await session.execute(delete(Persona).where(Persona.id.in_(persona_ids)))
    return int(result.rowcount or 0)


def _avatar_svg(persona: Persona) -> bytes:
    initials = f"{persona.nombre[:1]}{persona.apellido_paterno[:1]}".upper()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"
viewBox="0 0 256 256">
<rect width="256" height="256" fill="#155e75"/>
<circle cx="128" cy="94" r="48" fill="#fbbf24"/>
<path d="M32 240c12-58 58-82 96-82s84 24 96 82" fill="#0f766e"/>
<text x="128" y="236" text-anchor="middle" font-family="sans-serif"
font-size="32" fill="white">{initials}</text></svg>""".encode()


def _example_cv_pdf(persona: Persona) -> bytes:
    # A minimal, valid one-page PDF. Its text contains only fictional seed data.
    title = f"CV demo - {persona.nombre} {persona.apellido_paterno}".encode(
        "ascii", "replace"
    )
    stream = b"BT /F1 18 Tf 72 720 Td (" + title + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode())
        pdf.extend(content)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(pdf)


def _write_asset(storage_dir: Path, key: str, content: bytes) -> int:
    path = storage_dir / key
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != content:
        path.write_bytes(content)
    return len(content)


async def _ensure_demo_document(
    session: AsyncSession,
    *,
    persona: Persona,
    tipo: DocumentoTipo,
    key: str,
    title: str,
    mime_type: str,
    content: bytes,
    storage_dir: Path,
) -> None:
    size = _write_asset(storage_dir, key, content)
    existing = await session.execute(
        select(Documento).where(
            Documento.persona_id == persona.id,
            Documento.tipo == tipo,
            Documento.s3_key == key,
            Documento.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is None:
        session.add(
            Documento(
                persona_id=persona.id,
                subido_por_persona_id=persona.id,
                tipo=tipo,
                titulo=title,
                descripcion="Archivo ficticio generado para QA; no contiene PII real.",
                version=1,
                s3_key=key,
                mime_type=mime_type,
                size_bytes=size,
                is_current=True,
            )
        )


async def seed_demo_documents(
    session: AsyncSession, *, people: Sequence[Persona], storage_dir: Path
) -> None:
    """Create local, deterministic avatar/CV objects and their Documento rows."""
    for persona in people:
        prefix = f"demo/faker/personas/{persona.id}"
        await _ensure_demo_document(
            session,
            persona=persona,
            tipo=DocumentoTipo.FOTO,
            key=f"{prefix}/avatar.svg",
            title="Foto de perfil demo",
            mime_type="image/svg+xml",
            content=_avatar_svg(persona),
            storage_dir=storage_dir,
        )
        if persona.rol in {
            PersonRole.COORDINADOR_GENERAL,
            PersonRole.COORDINADOR,
            PersonRole.ENLACE,
        }:
            await _ensure_demo_document(
                session,
                persona=persona,
                tipo=DocumentoTipo.CV,
                key=f"{prefix}/cv-demo.pdf",
                title="Currículum demo",
                mime_type="application/pdf",
                content=_example_cv_pdf(persona),
                storage_dir=storage_dir,
            )


async def seed_faker_hierarchy(
    session: AsyncSession,
    *,
    config: SeedFakerConfig,
    password: str,
    append: bool,
) -> tuple[int, list[SeedAccountExport]]:
    """Insert planned people; returns (created_count, export_rows)."""
    created = 0
    exports: list[SeedAccountExport] = []
    nodes: dict[tuple[int, int | None, int | None], Persona] = {}
    seeded_people: list[Persona] = []

    for plan in iter_planned_people(config):
        parent = None
        parent_lookup = _parent_key(plan)
        if parent_lookup is not None:
            parent = nodes.get(parent_lookup)
            if parent is None:
                raise BootstrapError(
                    "Jerarquía inconsistente: falta el padre esperado en el seed Faker."
                )

        persona: Persona | None = None
        if plan.email:
            existing_user = await _find_user_by_email(session, plan.email)
            if existing_user:
                persona = existing_user.persona
                if persona is None or persona.rol is not plan.role:
                    raise BootstrapError(
                        f"Email Faker incompatible para {plan.email!r}."
                    )
        elif append:
            persona = await _find_amigo_by_telefono(session, plan.telefono)

        if persona is None:
            persona = Persona(
                rol=plan.role,
                parent_persona_id=parent.id if parent else None,
                nombre=plan.nombre,
                apellido_paterno=plan.apellido_paterno,
                apellido_materno=plan.apellido_materno,
                telefono=plan.telefono,
                latitud=plan.latitud,
                longitud=plan.longitud,
                fecha_registro=datetime.now(UTC),
            )
            session.add(persona)
            await session.flush()
            created += 1
            if plan.email and plan.role in AUTHENTICABLE_PERSON_ROLES:
                session.add(
                    AuthUser(
                        persona_id=persona.id,
                        email=plan.email,
                        password_hash=hash_password(password),
                        is_active=True,
                    )
                )

        # Existing Faker rows from a prior version are enriched on re-seed.
        persona.latitud = plan.latitud
        persona.longitud = plan.longitud

        if plan.role is not PersonRole.AMIGO:
            nodes[_node_key(plan)] = persona
        seeded_people.append(persona)

        if plan.role in AUTHENTICABLE_PERSON_ROLES:
            exports.append(
                SeedAccountExport(
                    email=plan.email,
                    rol=plan.role.value,
                    persona_id=persona.id,
                )
            )

    await seed_demo_documents(
        session, people=seeded_people, storage_dir=config.document_storage_dir
    )
    return created, exports


async def run_seed_faker(
    *,
    config: SeedFakerConfig,
    password: str,
    append: bool,
    fresh_subtree: bool,
) -> tuple[int, list[SeedAccountExport]]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            removed = 0
            if fresh_subtree:
                removed = await delete_faker_subtrees(
                    session, email_domain=config.email_domain
                )
                logger.info("Subárboles Faker eliminados: %d personas.", removed)
            created, exports = await seed_faker_hierarchy(
                session,
                config=config,
                password=password,
                append=append,
            )
            await session.commit()
            logger.info(
                "Seed Faker: %d personas nuevas (%d planeadas por configuración).",
                created,
                count_planned_people(config),
            )
            return created, exports
    finally:
        await engine.dispose()


def write_accounts_export(
    exports: Sequence[SeedAccountExport],
    *,
    path: Path | None,
    to_stdout: bool,
) -> None:
    payload = [row.as_dict() for row in exports]
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if to_stdout:
        print(text)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{text}\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera jerarquías ficticias masivas (Faker es_MX) para dev/QA."
    )
    parser.add_argument("--cg", type=int, default=2, metavar="N")
    parser.add_argument("--coordinadores-por-cg", type=int, default=3, metavar="N")
    parser.add_argument("--enlaces-por-coordinador", type=int, default=5, metavar="N")
    parser.add_argument("--amigos-por-enlace", type=int, default=10, metavar="N")
    parser.add_argument(
        "--email-domain",
        default=DEFAULT_DOMAIN,
        help=(
            f"Dominio ficticio para cuentas autenticables (default: {DEFAULT_DOMAIN})."
        ),
    )
    parser.add_argument(
        "--faker-seed",
        type=int,
        default=42_120,
        help="Semilla Faker para datos reproducibles.",
    )
    parser.add_argument(
        "--document-storage-dir",
        type=Path,
        default=Path("demo-document-storage"),
        metavar="PATH",
        help="Directorio local persistente para objetos FOTO/CV demo.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--append",
        action="store_true",
        help=(
            "Conserva subárboles Faker existentes; omite filas ya presentes (default)."
        ),
    )
    mode.add_argument(
        "--fresh-subtree",
        action="store_true",
        help="Elimina subárboles marcados con faker.* antes de insertar.",
    )
    parser.add_argument(
        "--export-json",
        type=Path,
        metavar="PATH",
        help="Escribe cuentas de prueba (email, rol, persona_id) en un archivo JSON.",
    )
    parser.add_argument(
        "--export-accounts",
        action="store_true",
        help="Imprime el JSON de cuentas de prueba en stdout.",
    )
    return parser


async def _run(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.cg < 1 or args.coordinadores_por_cg < 1:
        parser.error("cg y coordinadores-por-cg deben ser >= 1.")
    if args.enlaces_por_coordinador < 1 or args.amigos_por_enlace < 1:
        parser.error("enlaces-por-coordinador y amigos-por-enlace deben ser >= 1.")

    try:
        _validate_runtime()
        password = resolve_password()
        if len(password) < 8:
            raise BootstrapError(
                "La contraseña de seed debe tener al menos 8 caracteres."
            )
        config = SeedFakerConfig(
            coordinadores_generales=args.cg,
            coordinadores_por_cg=args.coordinadores_por_cg,
            enlaces_por_coordinador=args.enlaces_por_coordinador,
            amigos_por_enlace=args.amigos_por_enlace,
            email_domain=args.email_domain.strip().lower(),
            faker_seed=args.faker_seed,
            document_storage_dir=args.document_storage_dir,
        )
        _, exports = await run_seed_faker(
            config=config,
            password=password,
            append=not args.fresh_subtree,
            fresh_subtree=args.fresh_subtree,
        )
        if args.export_accounts or args.export_json:
            write_accounts_export(
                exports,
                path=args.export_json,
                to_stdout=args.export_accounts,
            )
    except BootstrapError as exc:
        logger.error("Seed Faker rechazado: %s", exc)
        return exc.exit_code
    except Exception:
        logger.exception("Falló el seed Faker.")
        return 1
    logger.info("Seed Faker aplicado correctamente.")
    return 0


def main_cli() -> None:
    sys.exit(asyncio.run(_run()))
