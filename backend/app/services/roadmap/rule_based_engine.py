from typing import Optional
from app.services.roadmap.knowledge_base import (
    SKILL_KNOWLEDGE_BASE,
    CATEGORY_ORDER,
    get_skill_info,
)


# Résolution des prérequis 

def resolve_prerequisites(
    missing_skills: list[str],
    acquired_skills: list[str],
) -> list[str]:
    acquired_set = {s.lower().strip() for s in acquired_skills}
    to_learn     = [s.lower().strip() for s in missing_skills]
    resolved     = []
    visited      = set()

    def _add_with_prereqs(skill: str):
        if skill in visited or skill in acquired_set:
            return
        visited.add(skill)

        info = get_skill_info(skill)
        if not info:
            resolved.append(skill)
            return

        # D'abord les prérequis récursivement
        for prereq in info.get("prereqs", []):
            if prereq not in acquired_set and prereq not in visited:
                _add_with_prereqs(prereq)

        resolved.append(skill)

    for skill in to_learn:
        _add_with_prereqs(skill)

    return resolved


# Tri par priorité et catégorie 

def sort_skills_by_learning_order(skills: list[str]) -> list[str]:
    def sort_key(skill: str):
        info     = get_skill_info(skill) or {}
        category = info.get("category", "zzz")
        priority = info.get("priority", 5)
        weeks    = info.get("weeks", 2)

        cat_order = CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else 99

        return (cat_order, priority, weeks)

    return sorted(skills, key=sort_key)


# Distribution sur les semaines 

def distribute_to_weeks(
    skills: list[str],
    total_weeks: int,
) -> list[dict]:
    if not skills:
        return []

    # Calculer les durées totales
    skill_weeks = []
    for skill in skills:
        info  = get_skill_info(skill) or {}
        weeks = max(1, round(info.get("weeks", 1)))
        skill_weeks.append((skill, weeks))

    total_estimated = sum(w for _, w in skill_weeks)

    # Adapter si le total dépasse la durée cible
    if total_estimated > total_weeks:
        scale  = total_weeks / total_estimated
        skill_weeks = [(s, max(1, round(w * scale))) for s, w in skill_weeks]

    # Assigner les semaines
    distribution = []
    current_week = 1

    for skill, weeks in skill_weeks:
        if current_week > total_weeks:
            break
        week_end = min(current_week + weeks - 1, total_weeks)
        distribution.append({
            "skill":           skill,
            "week_start":      current_week,
            "week_end":        week_end,
            "weeks_allocated": week_end - current_week + 1,
        })
        current_week = week_end + 1

    return distribution


# Génération des étapes 

def generate_steps_for_skill(
    skill:       str,
    week_start:  int,
    week_end:    int,
    user_level:  str = "débutant",
) -> list[dict]:
    info  = get_skill_info(skill)
    steps = []

    if not info:
        # Skill inconnu dans la KB → step générique
        steps.append({
            "week_number":  week_start,
            "title":        f"Apprendre {skill.title()}",
            "skill_name":   skill,
            "type":         "course",
            "resource_link": None,
            "description":  f"Se former sur {skill} via documentation officielle ou tutoriels.",
            "source":       "rule_based",
        })
        return steps

    courses  = info.get("courses", [])
    projects = info.get("projects", [])
    duration = week_end - week_start + 1

    # Étape 1 : Cours principal 
    if courses:
        # Choisir le cours adapté au niveau
        course = courses[0]  # Par défaut le premier
        if user_level in ("intermédiaire", "avancé") and len(courses) > 1:
            course = courses[1]  # Cours plus avancé

        steps.append({
            "week_number":  week_start,
            "title":        f"{skill.title()} — {course['title']}",
            "skill_name":   skill,
            "type":         "course",
            "resource_link": course["url"],
            "description":  f"Formation {skill.title()} sur {course['platform']} ({course['duration']}). "
                           f"Objectif : maîtriser les bases fondamentales.",
            "source":       "rule_based",
        })
    else:
        steps.append({
            "week_number":  week_start,
            "title":        f"Formation {skill.title()}",
            "skill_name":   skill,
            "type":         "course",
            "resource_link": None,
            "description":  f"Se former sur {skill.title()} via la documentation officielle.",
            "source":       "rule_based",
        })

    # Étape 2 : Mini-projet 
    if duration >= 2 and projects:
        project = projects[0]
        mid_week = week_start + max(1, duration // 2)

        steps.append({
            "week_number":  min(mid_week, week_end),
            "title":        f"Projet {skill.title()} : {project['title']}",
            "skill_name":   skill,
            "type":         "project",
            "resource_link": None,
            "description":  project["description"],
            "source":       "rule_based",
        })

    # Étape 3 : Ressource complémentaire 
    if duration >= 3 and len(courses) > 1:
        extra_course = courses[-1]  # Dernière ressource = plus approfondie
        steps.append({
            "week_number":  week_end,
            "title":        f"{skill.title()} approfondi — {extra_course['title']}",
            "skill_name":   skill,
            "type":         "reading",
            "resource_link": extra_course["url"],
            "description":  f"Approfondissement sur {extra_course['platform']} pour solidifier la maîtrise.",
            "source":       "rule_based",
        })

    return steps


# Moteur principal 

def generate_roadmap_rule_based(
    missing_skills:  list[str],
    acquired_skills: list[str] = None,
    duration_weeks:  int       = 8,
    user_level:      str       = "débutant",
    job_name:        str       = "",
) -> dict:
    acquired_skills = acquired_skills or []

    if not missing_skills:
        return {
            "job_name":      job_name,
            "duration_weeks": duration_weeks,
            "total_skills":  0,
            "skills_order":  [],
            "steps":         [],
            "summary":       {"courses_count": 0, "projects_count": 0, "weeks_used": 0},
            "engine":        "rule_based",
        }

    # 1. Résoudre les prérequis
    full_skills = resolve_prerequisites(missing_skills, acquired_skills)

    # 2. Trier dans l'ordre pédagogique
    ordered_skills = sort_skills_by_learning_order(full_skills)

    # 3. Distribuer sur les semaines
    distribution = distribute_to_weeks(ordered_skills, duration_weeks)

    # 4. Générer les étapes
    all_steps = []
    for item in distribution:
        steps = generate_steps_for_skill(
            skill      = item["skill"],
            week_start = item["week_start"],
            week_end   = item["week_end"],
            user_level = user_level,
        )
        all_steps.extend(steps)

    # 5. Trier par semaine
    all_steps.sort(key=lambda s: s["week_number"])

    # 6. Statistiques
    courses_count  = sum(1 for s in all_steps if s["type"] == "course")
    projects_count = sum(1 for s in all_steps if s["type"] == "project")
    weeks_used     = max((s["week_number"] for s in all_steps), default=0)

    return {
        "job_name":       job_name,
        "duration_weeks": duration_weeks,
        "total_skills":   len(ordered_skills),
        "skills_order":   ordered_skills,
        "steps":          all_steps,
        "summary": {
            "courses_count":  courses_count,
            "projects_count": projects_count,
            "weeks_used":     weeks_used,
        },
        "engine": "rule_based",
    }
