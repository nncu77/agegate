-- AgeGate database schema
-- =======================
--
-- Tables:
--   stores       — registered merchants
--   policies     — verification rules per store
--   audit_logs   — every verification call (no PII, no images)
--
-- Design notes:
--   - audit_logs is append-only (no UPDATE except for operator_override columns)
--   - policies has updated_at for correlating policy-at-time-of-decision
--   - All timestamps in UTC; convert at presentation layer

-- ===== stores =====

create table if not exists public.stores (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  owner_id    uuid not null references auth.users(id) on delete cascade,
  created_at  timestamptz not null default now()
);

create index if not exists stores_owner_id_idx on public.stores(owner_id);

-- ===== policies =====

create table if not exists public.policies (
  store_id              uuid primary key references public.stores(id) on delete cascade,
  threshold_age         smallint not null check (threshold_age between 0 and 100),
  buffer_years          smallint not null check (buffer_years between 0 and 20),
  min_face_confidence   real not null check (min_face_confidence between 0 and 1),
  updated_at            timestamptz not null default now()
);

-- Auto-update updated_at on row change.
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_policies_updated_at on public.policies;
create trigger trg_policies_updated_at
  before update on public.policies
  for each row execute function public.set_updated_at();

-- ===== audit_logs =====
-- Append-only ledger of every verification call.
-- Critical: this table contains NO biometric data, NO images, NO PII.
-- It is safe to retain indefinitely for compliance evidence.

create table if not exists public.audit_logs (
  id                  uuid primary key,  -- == request_id from API
  store_id            uuid not null references public.stores(id) on delete restrict,
  timestamp           timestamptz not null default now(),
  decision            text not null check (decision in ('pass', 'reject', 'manual_check')),
  reason              text not null,
  age_low             smallint not null,
  age_high            smallint not null,
  face_confidence     real not null,
  threshold_used      smallint not null,
  buffer_used         smallint not null,
  -- Operator-completed fields (populated via /audit/override):
  operator_override   text check (operator_override in ('pass', 'reject') or operator_override is null),
  operator_note       text,
  operator_acted_at   timestamptz
);

create index if not exists audit_logs_store_time_idx
  on public.audit_logs(store_id, timestamp desc);
create index if not exists audit_logs_decision_idx
  on public.audit_logs(store_id, decision);

-- Prevent UPDATE on append-only columns. Only operator_* columns can be filled in later.
create or replace function public.guard_audit_immutability()
returns trigger language plpgsql as $$
begin
  if (old.id, old.store_id, old.timestamp, old.decision, old.reason,
      old.age_low, old.age_high, old.face_confidence,
      old.threshold_used, old.buffer_used)
     is distinct from
     (new.id, new.store_id, new.timestamp, new.decision, new.reason,
      new.age_low, new.age_high, new.face_confidence,
      new.threshold_used, new.buffer_used) then
    raise exception 'audit_logs core columns are immutable';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_audit_immutable on public.audit_logs;
create trigger trg_audit_immutable
  before update on public.audit_logs
  for each row execute function public.guard_audit_immutability();

-- ===== Row Level Security =====
-- Store owners may only see their own data.

alter table public.stores      enable row level security;
alter table public.policies    enable row level security;
alter table public.audit_logs  enable row level security;

-- Drop-then-create makes this file idempotent: re-running the whole
-- migration in the SQL editor won't error on duplicate policy names.
drop policy if exists "Owners can view own stores"     on public.stores;
drop policy if exists "Owners can insert own stores"   on public.stores;
drop policy if exists "Owners can view own policies"   on public.policies;
drop policy if exists "Owners can upsert own policies" on public.policies;
drop policy if exists "Owners can view own audit logs" on public.audit_logs;

create policy "Owners can view own stores"
  on public.stores for select
  using (owner_id = auth.uid());

create policy "Owners can insert own stores"
  on public.stores for insert
  with check (owner_id = auth.uid());

create policy "Owners can view own policies"
  on public.policies for select
  using (store_id in (select id from public.stores where owner_id = auth.uid()));

create policy "Owners can upsert own policies"
  on public.policies for all
  using (store_id in (select id from public.stores where owner_id = auth.uid()))
  with check (store_id in (select id from public.stores where owner_id = auth.uid()));

create policy "Owners can view own audit logs"
  on public.audit_logs for select
  using (store_id in (select id from public.stores where owner_id = auth.uid()));

-- The backend service writes audit logs using the service_role key,
-- which bypasses RLS. Owner UI is read-only.
