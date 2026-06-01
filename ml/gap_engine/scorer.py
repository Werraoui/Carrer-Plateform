def compute_score(cv_skills, job_skills):

    total_weight = sum(job_skills.values())

    score = 0

    for skill in cv_skills:
        if skill in job_skills:
            score += job_skills[skill]

    if total_weight == 0:
        return 0

    return round((score/total_weight)*100,2)