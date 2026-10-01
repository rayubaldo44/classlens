import hashlib
import json
from functools import lru_cache

from app.database import Database, DatabaseError, get_database
from app.providers.analysis_store import AnalysisSnapshot
from app.providers.material_index.protocol import MaterialRecord, MaterialSearchHit
from app.schemas.analysis import AnalysisResponse
from app.schemas.assessment import AssessmentPreview, NormalizedResponse
from app.schemas.materials import LearningMaterial, MaterialChunk
from app.schemas.remediations import RemediationRecord
from app.schemas.results import FollowUpComparisonRecord
from app.services.assessment_intake import ParsedAssessment


def _json(value) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


class PostgresAnalysisStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(
        self,
        parsed: ParsedAssessment,
        result: AnalysisResponse,
        *,
        assessment_kind: str = "baseline",
        baseline_assessment_id: str | None = None,
    ) -> None:
        with self.database.connection() as connection, connection.transaction():
            self.save_in_connection(
                connection,
                parsed,
                result,
                assessment_kind=assessment_kind,
                baseline_assessment_id=baseline_assessment_id,
            )

    def save_in_connection(self, connection, parsed, result, *, assessment_kind, baseline_assessment_id) -> None:
        meta = parsed.preview.assessment
        connection.execute(
            """
            insert into assessments
              (id, assessment_kind, baseline_assessment_id, data_label, filename, title, subject,
               grade_level, topic, preview_json)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            on conflict (id) do nothing
            """,
            (
                result.assessment_id, assessment_kind, baseline_assessment_id, parsed.preview.data_label,
                parsed.preview.filename, meta.title, meta.subject, meta.grade_level, meta.topic,
                _json(parsed.preview.model_dump(mode="json")),
            ),
        )
        question_order: list[str] = []
        for response in parsed.responses:
            if response.question_id not in question_order:
                question_order.append(response.question_id)
        for position, external_key in enumerate(question_order):
            response = next(item for item in parsed.responses if item.question_id == external_key)
            connection.execute(
                """
                insert into questions (assessment_id, external_key, position, prompt, correct_answer)
                values (%s,%s,%s,%s,%s) on conflict (assessment_id, external_key) do nothing
                """,
                (result.assessment_id, external_key, position, response.question, response.correct_answer),
            )
        question_rows = connection.execute(
            "select id, external_key from questions where assessment_id=%s", (result.assessment_id,)
        ).fetchall()
        question_ids = {row[1]: row[0] for row in question_rows}
        for response in parsed.responses:
            connection.execute(
                """
                insert into student_responses
                  (question_id, student_key, row_number, response_text, answer_status, is_correct)
                values (%s,%s,%s,%s,%s,%s) on conflict (question_id, student_key) do nothing
                """,
                (
                    question_ids[response.question_id], response.student_id, response.row_number,
                    response.answer, response.answer_status, response.is_correct,
                ),
            )
        inserted = connection.execute(
            """
            insert into analysis_runs
              (id, assessment_id, status, embedding_model, embedding_dimension, preprocessing,
               grouping_algorithm, similarity_threshold, minimum_support, result_json)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            on conflict (id) do nothing returning id
            """,
            (
                result.analysis_id, result.assessment_id, result.status, result.embedding.model_id,
                result.embedding.dimension, result.embedding.preprocessing, result.grouping.algorithm,
                result.grouping.similarity_threshold, result.grouping.minimum_support,
                _json(result.model_dump(mode="json")),
            ),
        ).fetchone()
        if inserted is None:
            return
        response_rows = connection.execute(
            """
            select r.id, q.external_key, r.student_key
            from student_responses r join questions q on q.id=r.question_id
            where q.assessment_id=%s
            """,
            (result.assessment_id,),
        ).fetchall()
        response_ids = {(row[1], row[2]): row[0] for row in response_rows}
        for group in result.groups:
            group_row = connection.execute(
                """
                insert into misconception_groups
                  (analysis_id, public_id, question_id, provisional_label, interpretation_status,
                   support_count, eligible_response_count, coherence)
                values (%s,%s,%s,%s,%s,%s,%s,%s) returning id
                """,
                (
                    result.analysis_id, group.group_id, question_ids[group.question_id],
                    group.provisional_label, group.interpretation_status, group.support_count,
                    group.eligible_response_count, group.coherence,
                ),
            ).fetchone()[0]
            representative = {
                item.student_id: (rank, item.similarity_to_medoid)
                for rank, item in enumerate(group.representative_responses)
            }
            for student_id in group.member_student_ids:
                rep = representative.get(student_id)
                connection.execute(
                    """
                    insert into misconception_members
                      (group_id, response_id, is_representative, representative_rank, similarity_to_medoid)
                    values (%s,%s,%s,%s,%s)
                    """,
                    (
                        group_row, response_ids[(group.question_id, student_id)], rep is not None,
                        rep[0] if rep else None, rep[1] if rep else None,
                    ),
                )

    def get(self, analysis_id: str) -> AnalysisSnapshot | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                select a.preview_json, ar.result_json, a.id
                from analysis_runs ar join assessments a on a.id=ar.assessment_id
                where ar.id=%s
                """,
                (analysis_id,),
            ).fetchone()
            if row is None:
                return None
            responses = connection.execute(
                """
                select r.row_number, r.student_key, q.external_key, q.prompt, r.response_text,
                       q.correct_answer, r.answer_status, r.is_correct
                from student_responses r join questions q on q.id=r.question_id
                where q.assessment_id=%s order by r.row_number
                """,
                (row[2],),
            ).fetchall()
        parsed = ParsedAssessment(
            preview=AssessmentPreview.model_validate(row[0]),
            responses=[
                NormalizedResponse(
                    row_number=item[0], student_id=item[1], question_id=item[2], question=item[3],
                    answer=item[4], correct_answer=item[5], answer_status=item[6], is_correct=item[7],
                )
                for item in responses
            ],
        )
        return AnalysisSnapshot(parsed=parsed, result=AnalysisResponse.model_validate(row[1]))


class PostgresMaterialIndex:
    def __init__(self, database: Database) -> None:
        self.database = database
        self._vectors: dict[str, tuple[tuple[float, ...], ...]] = {}

    def upsert(self, record: MaterialRecord) -> None:
        material = record.material
        with self.database.connection() as connection, connection.transaction():
            connection.execute(
                """
                insert into learning_materials
                  (id,title,filename,source_kind,content_hash,chunk_count,chunk_size_chars,
                   chunk_overlap_chars,embedding_model,embedding_dimension)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (id) do update set title=excluded.title, filename=excluded.filename,
                  source_kind=excluded.source_kind, updated_at=now()
                """,
                (
                    material.material_id, material.title, material.filename, material.source_kind,
                    material.content_hash, material.chunk_count, material.chunk_size_chars,
                    material.chunk_overlap_chars, material.embedding_model, material.embedding_dimension,
                ),
            )
            for chunk in record.chunks:
                digest = hashlib.sha256(chunk.text.encode()).hexdigest()
                connection.execute(
                    """
                    insert into document_chunks
                      (material_id,public_id,ordinal,content,start_char,end_char,content_hash)
                    values (%s,%s,%s,%s,%s,%s,%s)
                    on conflict (material_id,public_id) do update set content=excluded.content,
                      start_char=excluded.start_char,end_char=excluded.end_char,content_hash=excluded.content_hash
                    """,
                    (material.material_id, chunk.chunk_id, chunk.chunk_index, chunk.text,
                     chunk.start_char, chunk.end_char, digest),
                )
        self._vectors[material.material_id] = record.embeddings

    def get(self, material_id: str) -> MaterialRecord | None:
        with self.database.connection() as connection:
            material = connection.execute(
                """
                select id,title,filename,source_kind,content_hash,chunk_count,chunk_size_chars,
                       chunk_overlap_chars,embedding_model,embedding_dimension
                from learning_materials where id=%s
                """,
                (material_id,),
            ).fetchone()
            if material is None:
                return None
            chunks = connection.execute(
                """
                select public_id,ordinal,content,start_char,end_char
                from document_chunks where material_id=%s order by ordinal
                """,
                (material_id,),
            ).fetchall()
        return MaterialRecord(
            material=LearningMaterial(
                material_id=material[0], title=material[1], filename=material[2], source_kind=material[3],
                content_hash=material[4], chunk_count=material[5], chunk_size_chars=material[6],
                chunk_overlap_chars=material[7], embedding_model=material[8], embedding_dimension=material[9],
            ),
            chunks=tuple(MaterialChunk(chunk_id=c[0], chunk_index=c[1], text=c[2], start_char=c[3], end_char=c[4]) for c in chunks),
            embeddings=self._vectors.get(material_id, ()),
        )

    def set_embeddings(self, material_id: str, embeddings: tuple[tuple[float, ...], ...]) -> None:
        self._vectors[material_id] = embeddings

    def search(self, material_id: str, query_embedding: list[float], limit: int) -> list[MaterialSearchHit]:
        record = self.get(material_id)
        if record is None or len(record.embeddings) != len(record.chunks):
            return []
        hits = [
            MaterialSearchHit(chunk=chunk, similarity=sum(a*b for a,b in zip(query_embedding, vector, strict=True)))
            for chunk, vector in zip(record.chunks, record.embeddings, strict=True)
        ]
        return sorted(hits, key=lambda hit: (-hit.similarity, hit.chunk.chunk_index))[:limit]


class PostgresRemediationStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(self, record: RemediationRecord) -> None:
        with self.database.connection() as connection, connection.transaction():
            existing = connection.execute("select status from interventions where id=%s for update", (record.remediation_id,)).fetchone()
            if existing is not None and existing[0] != "generated":
                raise DatabaseError("database_conflict", "This remediation has already reached a terminal review state.", retryable=False)
            connection.execute(
                """
                insert into interventions
                  (id,analysis_id,group_public_id,status,provider,model,prompt_version,generated_content,
                   edited_content,review_notes,record_json,created_at,updated_at)
                values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s,%s)
                on conflict (id) do update set status=excluded.status, edited_content=excluded.edited_content,
                  review_notes=excluded.review_notes, record_json=excluded.record_json, updated_at=excluded.updated_at
                """,
                (
                    record.remediation_id, record.analysis_id, record.group_id, record.status, record.provider,
                    record.model, record.prompt_version, _json(record.generated_content.model_dump(mode="json")),
                    _json(record.content.model_dump(mode="json")), record.review_notes,
                    _json(record.model_dump(mode="json")), record.created_at, record.updated_at,
                ),
            )
            for rank, source in enumerate(record.sources):
                connection.execute(
                    """
                    insert into intervention_sources
                      (intervention_id,material_id,chunk_public_id,retrieval_rank,relevance_score,
                       material_title,filename,content_snapshot,start_char,end_char)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing
                    """,
                    (record.remediation_id, source.material_id, source.chunk_id, rank, source.similarity,
                     source.material_title, source.filename, source.text, source.start_char, source.end_char),
                )

    def get(self, remediation_id: str) -> RemediationRecord | None:
        with self.database.connection() as connection:
            row = connection.execute("select record_json from interventions where id=%s", (remediation_id,)).fetchone()
        return RemediationRecord.model_validate(row[0]) if row else None


class PostgresResultsStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(self, record: FollowUpComparisonRecord) -> None:
        if record.trace is None:
            raise DatabaseError("database_invalid_relationship", "A persisted comparison requires a complete trace.", retryable=False)
        trace = record.trace
        with self.database.connection() as connection, connection.transaction():
            connection.execute(
                """
                insert into assessment_comparisons
                  (id,baseline_analysis_id,follow_up_analysis_id,baseline_group_public_id,
                   follow_up_group_public_id,intervention_id,status,matching_method,record_json,created_at)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                on conflict (id) do update set record_json=excluded.record_json
                """,
                (record.comparison_id, trace.baseline_analysis_id, trace.follow_up_analysis_id,
                 trace.baseline_group_id, trace.follow_up_group_id, trace.remediation_id,
                 record.status, trace.comparison_method, _json(record.model_dump(mode="json")), record.created_at),
            )

    def get(self, comparison_id: str) -> FollowUpComparisonRecord | None:
        with self.database.connection() as connection:
            row = connection.execute("select record_json from assessment_comparisons where id=%s", (comparison_id,)).fetchone()
        return FollowUpComparisonRecord.model_validate(row[0]) if row else None


@lru_cache(maxsize=1)
def get_postgres_analysis_store() -> PostgresAnalysisStore:
    return PostgresAnalysisStore(get_database())


@lru_cache(maxsize=1)
def get_postgres_material_index() -> PostgresMaterialIndex:
    return PostgresMaterialIndex(get_database())


@lru_cache(maxsize=1)
def get_postgres_remediation_store() -> PostgresRemediationStore:
    return PostgresRemediationStore(get_database())


@lru_cache(maxsize=1)
def get_postgres_results_store() -> PostgresResultsStore:
    return PostgresResultsStore(get_database())
