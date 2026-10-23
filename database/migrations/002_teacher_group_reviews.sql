begin;

create table if not exists analysis_group_review_states (
  analysis_id text primary key references analysis_runs(id) on delete restrict,
  revision integer not null check (revision >= 1),
  state_json jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists analysis_group_review_events (
  id uuid primary key default gen_random_uuid(),
  public_id text not null unique,
  analysis_id text not null references analysis_runs(id) on delete restrict,
  sequence integer not null check (sequence >= 1),
  action text not null check (action in ('rename', 'merge', 'dismiss', 'restore')),
  source_group_ids text[] not null check (cardinality(source_group_ids) >= 1),
  resulting_reviewed_group_id text not null,
  previous_state_json jsonb,
  next_state_json jsonb not null,
  review_note text,
  created_at timestamptz not null,
  unique (analysis_id, sequence)
);

create index if not exists group_review_events_analysis_idx
  on analysis_group_review_events(analysis_id, sequence);

alter table analysis_group_review_states enable row level security;
alter table analysis_group_review_events enable row level security;

alter table interventions
  add column if not exists reviewed_group_public_id text,
  add column if not exists source_group_public_ids text[];

update interventions
set reviewed_group_public_id = group_public_id,
    source_group_public_ids = array[group_public_id]
where reviewed_group_public_id is null or source_group_public_ids is null;

alter table interventions
  alter column reviewed_group_public_id set not null,
  alter column source_group_public_ids set not null;

alter table assessment_comparisons
  add column if not exists baseline_reviewed_group_public_id text,
  add column if not exists baseline_source_group_public_ids text[];

update assessment_comparisons
set baseline_reviewed_group_public_id = baseline_group_public_id,
    baseline_source_group_public_ids = array[baseline_group_public_id]
where baseline_reviewed_group_public_id is null or baseline_source_group_public_ids is null;

alter table assessment_comparisons
  alter column baseline_reviewed_group_public_id set not null,
  alter column baseline_source_group_public_ids set not null;

create index if not exists interventions_reviewed_group_idx
  on interventions(analysis_id, reviewed_group_public_id);

commit;
