# Timesheets (módulo: `timesheets`)

Registro de tiempo de empleados, horas facturables, aprobaciones y tarifas horarias.

## Propósito

El módulo Timesheets registra las entradas de tiempo orientadas a proyectos o facturables enviadas por los empleados. A diferencia de `time_control` (que registra eventos brutos de entrada/salida para cumplimiento normativo), los timesheets son entradas de trabajo introducidas manualmente que pasan por un flujo de aprobación antes de usarse para facturación o nómina.

Los empleados envían entradas de tiempo (fecha, horas, descripción, flag facturable, tarifa horaria), que los gestores revisan y aprueban o rechazan. Las entradas aprobadas alimentan los cálculos de nómina a través del hook `timesheets.entry_approved`. El módulo admite tarifas horarias configurables (por defecto global, sobrescritura por empleado) y genera informes por periodo.

Migrado del hub legacy (Django) a hub-next (FastAPI + SQLAlchemy 2.0).

## Modelos

- `TimesheetsSettings` — Singleton por hub. Flag facturable por defecto, flag require_approval, periodo de aprobación (weekly/biweekly/monthly).
- `HourlyRate` — Definición de tarifa con nombre, importe, ámbito de empleado opcional, flag is_default, is_active.
- `TimeEntry` — Registro de tiempo individual: referencia de empleado, fecha, hora de inicio/fin, duración, descripción, is_billable, referencia de tarifa horaria, estado (draft/submitted/approved/rejected), notas.
- `TimesheetApproval` — Registro de aprobación para un periodo de tiempo: empleado, inicio/fin del periodo, estado, referencia de aprobador, fecha de aprobación, notas.

## Rutas

`GET /m/timesheets/my_time` — Entradas de tiempo propias del empleado
`GET /m/timesheets/approvals` — Cola de aprobación del gestor
`GET /m/timesheets/reports` — Informes de horas y facturación
`GET /m/timesheets/rates` — Gestión de tarifas horarias
`GET /m/timesheets/settings` — Configuración del módulo

## Eventos

### Consumidos

`staff.member_deactivated` — Registrado para auditoría; las entradas pendientes permanecen pero quedan marcadas.

## Hooks

### Emitidos

`timesheets.entry_approved` — Se dispara tras aprobar una entrada de tiempo individual. Payload: `entry`.
`timesheets.period_approved` — Se dispara tras aprobar un periodo completo de timesheet. Payload: `approval`.

## Dependencias

- `staff`

## Precio

Gratuito.
