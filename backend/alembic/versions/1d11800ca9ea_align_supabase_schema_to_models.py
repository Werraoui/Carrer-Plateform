"""align supabase schema to models

Revision ID: 1d11800ca9ea
Revises: 21409087eb19
Create Date: 2026-04-25 16:04:38.718177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d11800ca9ea'
down_revision: Union[str, Sequence[str], None] = '21409087eb19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    # Backfill timestamps (safe if already non-null)
    op.execute(sa.text("update users set created_at = now() where created_at is null"))
    op.execute(sa.text("update cvs set uploaded_at = now() where uploaded_at is null"))
    op.execute(sa.text("update offers set scraped_at = now() where scraped_at is null"))
    op.execute(sa.text("update career_gap_analyses set created_at = now() where created_at is null"))
    op.execute(sa.text("update cv_optimizations set created_at = now() where created_at is null"))
    op.execute(sa.text("update interview_sessions set created_at = now() where created_at is null"))
    op.execute(sa.text("update roadmaps set created_at = now() where created_at is null"))
    
    op.alter_column("users", "created_at", nullable=False)
    op.alter_column("cvs", "uploaded_at", nullable=False)
    op.alter_column("offers", "scraped_at", nullable=False)
    op.alter_column("career_gap_analyses", "created_at", nullable=False)
    op.alter_column("cv_optimizations", "created_at", nullable=False)
    op.alter_column("interview_sessions", "created_at", nullable=False)
    op.alter_column("roadmaps", "created_at", nullable=False)


    # FK indexes (idempotent: avoid DuplicateTable if they already exist)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cvs_user_id ON public.cvs (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_target_jobs_user_id ON public.user_target_jobs (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_target_jobs_target_job_id ON public.user_target_jobs (target_job_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_cv_skills_cv_id ON public.cv_skills (cv_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cv_skills_skill_id ON public.cv_skills (skill_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_job_skills_target_job_id ON public.job_skills (target_job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_job_skills_skill_id ON public.job_skills (skill_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_offer_skills_offer_id ON public.offer_skills (offer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_offer_skills_skill_id ON public.offer_skills (skill_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_gap_details_career_gap_id ON public.gap_details (career_gap_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_gap_details_skill_id ON public.gap_details (skill_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_career_gap_analyses_user_target_job_id ON public.career_gap_analyses (user_target_job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_career_gap_analyses_cv_id ON public.career_gap_analyses (cv_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_career_gap_analyses_offer_id ON public.career_gap_analyses (offer_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_roadmaps_user_target_job_id ON public.roadmaps (user_target_job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_roadmaps_career_gap_id ON public.roadmaps (career_gap_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_roadmap_steps_roadmap_id ON public.roadmap_steps (roadmap_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_roadmap_steps_skill_id ON public.roadmap_steps (skill_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_interview_sessions_user_target_job_id ON public.interview_sessions (user_target_job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_interview_sessions_offer_id ON public.interview_sessions (offer_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_interview_questions_session_id ON public.interview_questions (session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_interview_questions_related_skill_id ON public.interview_questions (related_skill_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_cv_optimizations_cv_id ON public.cv_optimizations (cv_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cv_optimizations_offer_id ON public.cv_optimizations (offer_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_user_skill_progress_user_id ON public.user_skill_progress (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_skill_progress_skill_id ON public.user_skill_progress (skill_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_skill_progress_roadmap_step_id ON public.user_skill_progress (roadmap_step_id)")

    # Optional unique indexes (only if you really want them; idempotent)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON public.users (email)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_skills_name ON public.skills (name)")

    # Unique constraints (idempotent)
    op.execute("""
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_cv_skill') THEN
    ALTER TABLE public.cv_skills ADD CONSTRAINT uq_cv_skill UNIQUE (cv_id, skill_id);
  END IF;
END $$;
""")
    op.execute("""
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_job_skill') THEN
    ALTER TABLE public.job_skills ADD CONSTRAINT uq_job_skill UNIQUE (target_job_id, skill_id);
  END IF;
END $$;
""")
    op.execute("""
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_offer_skill') THEN
    ALTER TABLE public.offer_skills ADD CONSTRAINT uq_offer_skill UNIQUE (offer_id, skill_id);
  END IF;
END $$;
""")

def downgrade() -> None:
    """Downgrade schema."""
    pass
