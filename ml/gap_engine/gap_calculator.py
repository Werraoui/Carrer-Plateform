def calculate_gap(cv_skills, market_skills):

    cv_set = set(cv_skills)
    market_set = set(market_skills)

    acquired = list(cv_set & market_set)
    missing = list(market_set - cv_set)

    match_percentage = 0

    if len(market_set) > 0:
        match_percentage = (len(acquired)/len(market_set))*100

    return {
        "acquired": acquired,
        "missing": missing,
        "match_percentage": round(match_percentage,2)
    }