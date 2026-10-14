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

commit;
