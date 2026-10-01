begin;

create extension if not exists pgcrypto;

create table if not exists assessments (
  id text primary key,
  assessment_kind text not null check (assessment_kind in ('baseline', 'follow_up')),
  baseline_assessment_id text references assessments(id) on delete restrict,
  data_label text not null check (data_label in ('teacher_upload', 'synthetic_demo')),
  filename text not null,
  title text not null,
  subject text not null,
  grade_level text not null,
  topic text not null,
  preview_json jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((assessment_kind = 'baseline' and baseline_assessment_id is null) or
         (assessment_kind = 'follow_up' and baseline_assessment_id is not null))
);

create table if not exists questions (
  id uuid primary key default gen_random_uuid(),
  assessment_id text not null references assessments(id) on delete restrict,
  external_key text not null,
  position integer not null check (position >= 0),
  prompt text not null,
  correct_answer text not null,
  unique (assessment_id, external_key)
);

create table if not exists student_responses (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references questions(id) on delete restrict,
  student_key text not null,
  row_number integer not null check (row_number >= 2),
  response_text text not null,
  answer_status text not null check (answer_status in ('answered', 'blank')),
  is_correct boolean not null,
  created_at timestamptz not null default now(),
  unique (question_id, student_key),
  check (not (answer_status = 'blank' and is_correct))
);

create table if not exists analysis_runs (
  id text primary key,
  assessment_id text not null references assessments(id) on delete restrict,
  status text not null check (status in ('completed', 'insufficient_data')),
  embedding_model text not null,
  embedding_dimension integer not null check (embedding_dimension >= 0),
  preprocessing text not null,
  grouping_algorithm text not null,
  similarity_threshold double precision not null check (similarity_threshold > 0 and similarity_threshold <= 1),
  minimum_support integer not null check (minimum_support >= 1),
  result_json jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists misconception_groups (
  id uuid primary key default gen_random_uuid(),
  analysis_id text not null references analysis_runs(id) on delete restrict,
  public_id text not null,
  question_id uuid not null references questions(id) on delete restrict,
  provisional_label text not null,
  interpretation_status text not null,
  support_count integer not null check (support_count > 0),
  eligible_response_count integer not null check (eligible_response_count >= support_count),
  coherence double precision not null,
  created_at timestamptz not null default now(),
  unique (analysis_id, public_id)
);

create table if not exists misconception_members (
  group_id uuid not null references misconception_groups(id) on delete restrict,
  response_id uuid not null references student_responses(id) on delete restrict,
  is_representative boolean not null default false,
  representative_rank integer,
  similarity_to_medoid double precision,
  primary key (group_id, response_id),
  check (representative_rank is null or representative_rank >= 0)
);

create table if not exists learning_materials (
  id text primary key,
  title text not null,
  filename text not null,
  source_kind text not null check (source_kind in ('teacher_upload', 'synthetic_demo')),
  content_hash text not null unique,
  chunk_count integer not null check (chunk_count > 0),
  chunk_size_chars integer not null check (chunk_size_chars > 0),
  chunk_overlap_chars integer not null check (chunk_overlap_chars >= 0),
  embedding_model text not null,
  embedding_dimension integer not null check (embedding_dimension > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  material_id text not null references learning_materials(id) on delete restrict,
  public_id text not null,
  ordinal integer not null check (ordinal >= 0),
  content text not null,
  start_char integer not null check (start_char >= 0),
  end_char integer not null check (end_char > start_char),
  content_hash text not null,
  unique (material_id, public_id),
  unique (material_id, ordinal)
);

create table if not exists interventions (
  id text primary key,
  analysis_id text not null,
  group_public_id text not null,
  status text not null check (status in ('generated', 'approved', 'rejected')),
  provider text not null,
  model text not null,
  prompt_version text not null,
  generated_content jsonb not null,
  edited_content jsonb not null,
  review_notes text,
  record_json jsonb not null,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  foreign key (analysis_id, group_public_id)
    references misconception_groups(analysis_id, public_id) on delete restrict
);

create table if not exists intervention_sources (
  intervention_id text not null references interventions(id) on delete restrict,
  material_id text not null references learning_materials(id) on delete restrict,
  chunk_public_id text not null,
  retrieval_rank integer not null check (retrieval_rank >= 0),
  relevance_score double precision not null,
  material_title text not null,
  filename text not null,
  content_snapshot text not null,
  start_char integer not null,
  end_char integer not null,
  primary key (intervention_id, material_id, chunk_public_id),
  foreign key (material_id, chunk_public_id)
    references document_chunks(material_id, public_id) on delete restrict
);

create table if not exists assessment_comparisons (
  id text primary key,
  baseline_analysis_id text not null references analysis_runs(id) on delete restrict,
  follow_up_analysis_id text not null references analysis_runs(id) on delete restrict,
  baseline_group_public_id text not null,
  follow_up_group_public_id text,
  intervention_id text not null references interventions(id) on delete restrict,
  status text not null check (status in ('completed', 'insufficient_data')),
  matching_method text not null,
  record_json jsonb not null,
  created_at timestamptz not null,
  foreign key (baseline_analysis_id, baseline_group_public_id)
    references misconception_groups(analysis_id, public_id) on delete restrict,
  foreign key (follow_up_analysis_id, follow_up_group_public_id)
    references misconception_groups(analysis_id, public_id) on delete restrict
);

create index if not exists questions_assessment_idx on questions(assessment_id);
create index if not exists responses_question_correct_idx on student_responses(question_id, is_correct);
create index if not exists analysis_assessment_idx on analysis_runs(assessment_id, created_at desc);
create index if not exists groups_analysis_idx on misconception_groups(analysis_id);
create index if not exists members_response_idx on misconception_members(response_id);
create index if not exists chunks_material_idx on document_chunks(material_id, ordinal);
create index if not exists interventions_group_idx on interventions(analysis_id, group_public_id);
create index if not exists comparisons_baseline_idx on assessment_comparisons(baseline_analysis_id, created_at desc);

alter table assessments enable row level security;
alter table questions enable row level security;
alter table student_responses enable row level security;
alter table analysis_runs enable row level security;
alter table misconception_groups enable row level security;
alter table misconception_members enable row level security;
alter table learning_materials enable row level security;
alter table document_chunks enable row level security;
alter table interventions enable row level security;
alter table intervention_sources enable row level security;
alter table assessment_comparisons enable row level security;

commit;
