from typing import Optional


# Structure d'une ressource 

# Chaque skill → dict avec :
#   "weeks"      : durée d'apprentissage estimée
#   "category"   : groupe logique (fondations, data_eng, ml, cloud, etc.)
#   "priority"   : 1=critique, 2=important, 3=utile
#   "prereqs"    : liste de skills à apprendre AVANT celui-ci
#   "courses"    : liste de cours gratuits [{title, url, platform, duration}]
#   "projects"   : liste de projets pratiques [{title, description, difficulty}]

SKILL_KNOWLEDGE_BASE: dict = {

    


    "python": {
        "weeks": 3,
        "category": "languages",
        "priority": 1,
        "prereqs": [],
        "courses": [
            {"title": "Python for Everybody",        "url": "https://www.coursera.org/specializations/python",      "platform": "Coursera",  "duration": "~20h"},
            {"title": "CS50P – Python (Harvard)",    "url": "https://cs50.harvard.edu/python/",                     "platform": "edX",       "duration": "~40h"},
            {"title": "Real Python Tutorials",       "url": "https://realpython.com/",                              "platform": "RealPython","duration": "libre"},
        ],
        "projects": [
            {"title": "Analyseur de logs",           "description": "Parser des fichiers log Apache et extraire des statistiques (top IPs, erreurs)", "difficulty": "débutant"},
            {"title": "CLI de gestion de tâches",    "description": "Application en ligne de commande avec argparse, lecture/écriture JSON",          "difficulty": "débutant"},
            {"title": "Web scraper simple",          "description": "Scraper un site avec requests + BeautifulSoup et sauvegarder en CSV",            "difficulty": "intermédiaire"},
        ],
    },

    "sql": {
        "weeks": 2,
        "category": "databases",
        "priority": 1,
        "prereqs": [],
        "courses": [
            {"title": "SQL for Data Science",        "url": "https://www.coursera.org/learn/sql-for-data-science", "platform": "Coursera",  "duration": "~15h"},
            {"title": "Mode Analytics SQL Tutorial", "url": "https://mode.com/sql-tutorial/",                      "platform": "Mode",      "duration": "~10h"},
            {"title": "SQLZoo Interactive",          "url": "https://sqlzoo.net/",                                 "platform": "SQLZoo",    "duration": "~8h"},
        ],
        "projects": [
            {"title": "Analyse ventes e-commerce",  "description": "Requêtes complexes sur dataset Olist (Kaggle) : top produits, churn, cohortes", "difficulty": "intermédiaire"},
            {"title": "Dashboard SQL pur",          "description": "Créer des vues et procédures stockées pour un système de reporting",             "difficulty": "intermédiaire"},
        ],
    },

    "r": {
        "weeks": 2,
        "category": "languages",
        "priority": 3,
        "prereqs": [],
        "courses": [
            {"title": "R for Data Science (livre)",  "url": "https://r4ds.had.co.nz/",                            "platform": "gratuit",   "duration": "~30h"},
            {"title": "Statistical Learning (Stanford)", "url": "https://www.statlearning.com/",                   "platform": "gratuit",   "duration": "~40h"},
        ],
        "projects": [
            {"title": "Analyse statistique dataset", "description": "EDA + tests statistiques + visualisations ggplot2 sur un dataset Kaggle",      "difficulty": "intermédiaire"},
        ],
    },

    "scala": {
        "weeks": 3,
        "category": "languages",
        "priority": 2,
        "prereqs": ["java"],
        "courses": [
            {"title": "Functional Programming in Scala", "url": "https://www.coursera.org/specializations/scala", "platform": "Coursera",  "duration": "~30h"},
        ],
        "projects": [
            {"title": "Pipeline Spark en Scala",     "description": "Réécrire un job Python Spark en Scala pour comparaison performances",          "difficulty": "avancé"},
        ],
    },

    
    # DATA ENGINEERING
    

    "spark": {
        "weeks": 2,
        "category": "data_engineering",
        "priority": 1,
        "prereqs": ["python", "sql"],
        "courses": [
            {"title": "Apache Spark with Python (Udemy)", "url": "https://www.udemy.com/course/taming-big-data-with-apache-spark-hands-on/", "platform": "Udemy",    "duration": "~15h"},
            {"title": "Spark Documentation officielle",  "url": "https://spark.apache.org/docs/latest/",                                    "platform": "Apache",   "duration": "référence"},
            {"title": "Databricks Learning",             "url": "https://learn.databricks.com/",                                            "platform": "Databricks","duration": "~10h"},
        ],
        "projects": [
            {"title": "ETL batch avec PySpark",      "description": "Ingérer un CSV volumineux (>1GB), transformer et écrire en Parquet partitionné",  "difficulty": "intermédiaire"},
            {"title": "Analyse logs avec Spark SQL", "description": "Traiter des logs serveur avec Spark SQL et produire un rapport agrégé",            "difficulty": "intermédiaire"},
        ],
    },

    "airflow": {
        "weeks": 2,
        "category": "data_engineering",
        "priority": 1,
        "prereqs": ["python", "docker"],
        "courses": [
            {"title": "The Complete Hands-On Intro to Apache Airflow", "url": "https://www.udemy.com/course/the-complete-hands-on-course-to-master-apache-airflow/", "platform": "Udemy",   "duration": "~8h"},
            {"title": "Airflow Documentation",       "url": "https://airflow.apache.org/docs/",                                             "platform": "Apache",   "duration": "référence"},
        ],
        "projects": [
            {"title": "Pipeline ETL orchestré",      "description": "DAG Airflow qui extrait des données d'une API, transforme et charge en PostgreSQL", "difficulty": "intermédiaire"},
            {"title": "Pipeline de scraping planifié","description": "DAG qui lance le scraper quotidiennement et envoie un rapport email",              "difficulty": "intermédiaire"},
        ],
    },

    "kafka": {
        "weeks": 2,
        "category": "data_engineering",
        "priority": 2,
        "prereqs": ["python"],
        "courses": [
            {"title": "Apache Kafka Series (Udemy)", "url": "https://www.udemy.com/course/apache-kafka/",                                   "platform": "Udemy",    "duration": "~15h"},
            {"title": "Confluent Kafka Tutorials",   "url": "https://developer.confluent.io/tutorials/",                                    "platform": "Confluent","duration": "~10h"},
        ],
        "projects": [
            {"title": "Streaming de données Twitter", "description": "Producer qui envoie des tweets en temps réel, Consumer qui analyse le sentiment", "difficulty": "avancé"},
        ],
    },

    "dbt": {
        "weeks": 1,
        "category": "data_engineering",
        "priority": 2,
        "prereqs": ["sql"],
        "courses": [
            {"title": "dbt Fundamentals (officiel)",  "url": "https://courses.getdbt.com/courses/fundamentals",                             "platform": "dbt",      "duration": "~5h"},
            {"title": "dbt Documentation",            "url": "https://docs.getdbt.com/",                                                   "platform": "dbt",      "duration": "référence"},
        ],
        "projects": [
            {"title": "Modélisation data warehouse",  "description": "Créer des modèles dbt (staging, marts) sur un dataset e-commerce",   "difficulty": "intermédiaire"},
        ],
    },

    "etl": {
        "weeks": 1,
        "category": "data_engineering",
        "priority": 1,
        "prereqs": ["python", "sql"],
        "courses": [
            {"title": "ETL and Data Pipelines with Shell, Airflow and Kafka", "url": "https://www.coursera.org/learn/etl-and-data-pipelines-shell-airflow-kafka", "platform": "Coursera", "duration": "~15h"},
        ],
        "projects": [
            {"title": "Pipeline ETL from scratch",   "description": "Extract depuis API REST, Transform avec pandas, Load dans PostgreSQL",              "difficulty": "intermédiaire"},
        ],
    },

    "data warehouse": {
        "weeks": 1,
        "category": "data_engineering",
        "priority": 2,
        "prereqs": ["sql"],
        "courses": [
            {"title": "Data Warehousing for Business Intelligence", "url": "https://www.coursera.org/specializations/data-warehousing", "platform": "Coursera", "duration": "~20h"},
        ],
        "projects": [
            {"title": "Mini data warehouse",         "description": "Concevoir un schéma en étoile (facts/dimensions) et charger des données historiques", "difficulty": "intermédiaire"},
        ],
    },

    "data lake": {
        "weeks": 1,
        "category": "data_engineering",
        "priority": 2,
        "prereqs": ["python", "aws"],
        "courses": [
            {"title": "Data Lakes on AWS",           "url": "https://aws.amazon.com/training/",                                             "platform": "AWS",      "duration": "~10h"},
        ],
        "projects": [
            {"title": "Data Lake sur S3",            "description": "Ingérer des fichiers bruts sur S3, cataloguer avec Glue, requêter avec Athena",      "difficulty": "avancé"},
        ],
    },

  
    # MACHINE LEARNING
   

    "machine learning": {
        "weeks": 4,
        "category": "ml",
        "priority": 1,
        "prereqs": ["python", "pandas", "numpy"],
        "courses": [
            {"title": "Machine Learning Specialization (Andrew Ng)", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "platform": "Coursera", "duration": "~90h"},
            {"title": "Hands-On ML with Scikit-Learn (livre)",       "url": "https://github.com/ageron/handson-ml3",                                 "platform": "GitHub",   "duration": "~60h"},
            {"title": "Fast.ai Practical Deep Learning",             "url": "https://course.fast.ai/",                                               "platform": "fast.ai",  "duration": "~30h"},
        ],
        "projects": [
            {"title": "Prédiction de churn",         "description": "Modèle de classification sur dataset télécom, avec feature engineering et évaluation", "difficulty": "intermédiaire"},
            {"title": "Système de recommandation",   "description": "Collaborative filtering sur dataset MovieLens",                                         "difficulty": "avancé"},
        ],
    },

    "deep learning": {
        "weeks": 4,
        "category": "ml",
        "priority": 2,
        "prereqs": ["machine learning", "python"],
        "courses": [
            {"title": "Deep Learning Specialization (Andrew Ng)", "url": "https://www.coursera.org/specializations/deep-learning", "platform": "Coursera", "duration": "~80h"},
            {"title": "MIT 6.S191 Introduction to Deep Learning", "url": "http://introtodeeplearning.com/",                       "platform": "MIT",      "duration": "~20h"},
        ],
        "projects": [
            {"title": "Classification d'images CNN",  "description": "ResNet fine-tuné sur dataset custom avec PyTorch",                                    "difficulty": "avancé"},
        ],
    },

    "nlp": {
        "weeks": 3,
        "category": "ml",
        "priority": 2,
        "prereqs": ["machine learning", "python"],
        "courses": [
            {"title": "NLP with HuggingFace (cours officiel)", "url": "https://huggingface.co/learn/nlp-course/chapter1/1", "platform": "HuggingFace", "duration": "~20h"},
            {"title": "Stanford CS224N",                        "url": "https://web.stanford.edu/class/cs224n/",            "platform": "Stanford",    "duration": "~40h"},
        ],
        "projects": [
            {"title": "Analyseur de CV (NER)",        "description": "Fine-tuner BERT pour extraire les skills depuis des textes de CV",                   "difficulty": "avancé"},
            {"title": "Chatbot FAQ",                  "description": "Système de Q&A avec sentence-transformers et recherche sémantique",                  "difficulty": "intermédiaire"},
        ],
    },

    "scikit-learn": {
        "weeks": 1,
        "category": "ml",
        "priority": 1,
        "prereqs": ["python", "pandas", "numpy"],
        "courses": [
            {"title": "Scikit-learn Documentation officielle", "url": "https://scikit-learn.org/stable/tutorial/",       "platform": "sklearn",  "duration": "~10h"},
        ],
        "projects": [
            {"title": "Pipeline ML complet",          "description": "Pipeline sklearn avec preprocessing, feature selection, GridSearchCV et évaluation", "difficulty": "intermédiaire"},
        ],
    },

    "tensorflow": {
        "weeks": 2,
        "category": "ml",
        "priority": 2,
        "prereqs": ["python", "machine learning"],
        "courses": [
            {"title": "TensorFlow Developer Certificate", "url": "https://www.coursera.org/professional-certificates/tensorflow-in-practice", "platform": "Coursera", "duration": "~40h"},
        ],
        "projects": [
            {"title": "Modèle de classification texte", "description": "Classifier des sentiments avec LSTM/BERT via TensorFlow",                         "difficulty": "avancé"},
        ],
    },

    "pytorch": {
        "weeks": 2,
        "category": "ml",
        "priority": 2,
        "prereqs": ["python", "machine learning"],
        "courses": [
            {"title": "PyTorch for Deep Learning (Zero to Mastery)", "url": "https://www.learnpytorch.io/",              "platform": "gratuit",  "duration": "~40h"},
            {"title": "PyTorch Documentation officielle",            "url": "https://pytorch.org/tutorials/",            "platform": "PyTorch",  "duration": "référence"},
        ],
        "projects": [
            {"title": "Réseau de neurones custom",    "description": "Implémenter et entraîner un modèle from scratch sur MNIST puis dataset custom",     "difficulty": "intermédiaire"},
        ],
    },

    "mlflow": {
        "weeks": 1,
        "category": "ml",
        "priority": 2,
        "prereqs": ["machine learning", "python"],
        "courses": [
            {"title": "MLflow Documentation",         "url": "https://mlflow.org/docs/latest/tutorials-and-examples/",  "platform": "MLflow",   "duration": "~5h"},
        ],
        "projects": [
            {"title": "MLOps pipeline basique",       "description": "Tracker des expériences ML avec MLflow, registre de modèles, déploiement local",    "difficulty": "intermédiaire"},
        ],
    },

    
    # DATA MANIPULATION
    

    "pandas": {
        "weeks": 1,
        "category": "data_manipulation",
        "priority": 1,
        "prereqs": ["python"],
        "courses": [
            {"title": "Pandas Documentation officielle", "url": "https://pandas.pydata.org/docs/getting_started/tutorials.html", "platform": "pandas",   "duration": "~10h"},
            {"title": "Kaggle Pandas Course",            "url": "https://www.kaggle.com/learn/pandas",                           "platform": "Kaggle",   "duration": "~4h"},
        ],
        "projects": [
            {"title": "EDA dataset Kaggle",           "description": "Analyse exploratoire complète (nettoyage, stats, visualisation) sur un dataset Kaggle", "difficulty": "débutant"},
        ],
    },

    "numpy": {
        "weeks": 1,
        "category": "data_manipulation",
        "priority": 1,
        "prereqs": ["python"],
        "courses": [
            {"title": "NumPy Quickstart",             "url": "https://numpy.org/doc/stable/user/quickstart.html",                "platform": "numpy",    "duration": "~5h"},
        ],
        "projects": [
            {"title": "Algèbre linéaire from scratch", "description": "Implémenter régression linéaire et PCA avec NumPy uniquement (sans sklearn)",      "difficulty": "intermédiaire"},
        ],
    },

   
    # CLOUD & DEVOPS
   

    "docker": {
        "weeks": 1,
        "category": "devops",
        "priority": 1,
        "prereqs": ["linux"],
        "courses": [
            {"title": "Docker & Kubernetes (Udemy)",  "url": "https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/", "platform": "Udemy",    "duration": "~20h"},
            {"title": "Play with Docker",             "url": "https://labs.play-with-docker.com/",                                    "platform": "gratuit",  "duration": "~5h"},
        ],
        "projects": [
            {"title": "Containeriser l'API backend",  "description": "Dockerfile + docker-compose pour FastAPI + PostgreSQL + Redis",                      "difficulty": "intermédiaire"},
        ],
    },

    "kubernetes": {
        "weeks": 2,
        "category": "devops",
        "priority": 2,
        "prereqs": ["docker"],
        "courses": [
            {"title": "Kubernetes for Beginners",     "url": "https://www.udemy.com/course/learn-kubernetes/",                      "platform": "Udemy",    "duration": "~8h"},
            {"title": "Kubernetes Documentation",     "url": "https://kubernetes.io/docs/tutorials/",                               "platform": "k8s",      "duration": "référence"},
        ],
        "projects": [
            {"title": "Déploiement sur Minikube",     "description": "Déployer l'application multi-service sur un cluster local Minikube",                "difficulty": "avancé"},
        ],
    },

    "aws": {
        "weeks": 3,
        "category": "cloud",
        "priority": 1,
        "prereqs": ["linux", "docker"],
        "courses": [
            {"title": "AWS Cloud Practitioner (officiel)", "url": "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/", "platform": "AWS",      "duration": "~6h"},
            {"title": "AWS Solutions Architect (A Cloud Guru)", "url": "https://acloudguru.com/course/aws-certified-solutions-architect-associate-saa-c03", "platform": "ACG", "duration": "~40h"},
        ],
        "projects": [
            {"title": "Pipeline serverless AWS",      "description": "Lambda + S3 + RDS : pipeline de traitement de fichiers uploadés",                   "difficulty": "avancé"},
            {"title": "Déploiement EC2 + RDS",        "description": "Déployer l'API FastAPI sur EC2 avec RDS PostgreSQL et un Load Balancer",            "difficulty": "avancé"},
        ],
    },

    "gcp": {
        "weeks": 2,
        "category": "cloud",
        "priority": 2,
        "prereqs": ["linux"],
        "courses": [
            {"title": "Google Cloud Fundamentals",    "url": "https://www.cloudskillsboost.google/course_templates/60", "platform": "Google",   "duration": "~8h"},
        ],
        "projects": [
            {"title": "Pipeline BigQuery + Dataflow", "description": "Ingérer et traiter des données sur GCP avec BigQuery et Dataflow",                  "difficulty": "avancé"},
        ],
    },

    "azure": {
        "weeks": 2,
        "category": "cloud",
        "priority": 2,
        "prereqs": ["linux"],
        "courses": [
            {"title": "Azure Fundamentals AZ-900",    "url": "https://learn.microsoft.com/en-us/training/paths/azure-fundamentals/", "platform": "Microsoft", "duration": "~10h"},
        ],
        "projects": [
            {"title": "Data Factory pipeline",        "description": "Pipeline ETL avec Azure Data Factory + Azure SQL Database",                         "difficulty": "avancé"},
        ],
    },

    "terraform": {
        "weeks": 1,
        "category": "devops",
        "priority": 2,
        "prereqs": ["aws"],
        "courses": [
            {"title": "HashiCorp Terraform Associate", "url": "https://developer.hashicorp.com/terraform/tutorials", "platform": "HashiCorp", "duration": "~10h"},
        ],
        "projects": [
            {"title": "Infrastructure as Code",       "description": "Provisionner un VPC + EC2 + RDS sur AWS avec Terraform",                           "difficulty": "avancé"},
        ],
    },

    "linux": {
        "weeks": 1,
        "category": "devops",
        "priority": 1,
        "prereqs": [],
        "courses": [
            {"title": "Linux Command Line Basics",    "url": "https://www.udacity.com/course/linux-command-line-basics--ud595", "platform": "Udacity",  "duration": "~5h"},
            {"title": "The Missing Semester (MIT)",   "url": "https://missing.csail.mit.edu/",                                  "platform": "MIT",      "duration": "~10h"},
        ],
        "projects": [
            {"title": "Scripts d'automatisation",     "description": "Scripts Bash pour monitoring système, backup automatique et alertes",               "difficulty": "débutant"},
        ],
    },

    "ci/cd": {
        "weeks": 1,
        "category": "devops",
        "priority": 2,
        "prereqs": ["git", "docker"],
        "courses": [
            {"title": "GitHub Actions Documentation", "url": "https://docs.github.com/en/actions",                                  "platform": "GitHub",   "duration": "~8h"},
            {"title": "GitLab CI/CD",                 "url": "https://docs.gitlab.com/ee/ci/",                                     "platform": "GitLab",   "duration": "~8h"},
        ],
        "projects": [
            {"title": "Pipeline CI/CD complet",       "description": "GitHub Actions : tests automatiques + build Docker + déploiement sur serveur",     "difficulty": "intermédiaire"},
        ],
    },

    "git": {
        "weeks": 0.5,
        "category": "tools",
        "priority": 1,
        "prereqs": [],
        "courses": [
            {"title": "Pro Git (livre gratuit)",      "url": "https://git-scm.com/book/fr/v2",                                     "platform": "gratuit",  "duration": "~10h"},
            {"title": "Learn Git Branching",          "url": "https://learngitbranching.js.org/?locale=fr_FR",                    "platform": "interactif","duration": "~3h"},
        ],
        "projects": [
            {"title": "Workflow Git en équipe",       "description": "Pratiquer gitflow : branches, PRs, merge, résolution de conflits sur un vrai projet","difficulty": "débutant"},
        ],
    },

   
    # DATABASES
    

    "postgresql": {
        "weeks": 1,
        "category": "databases",
        "priority": 1,
        "prereqs": ["sql"],
        "courses": [
            {"title": "PostgreSQL Tutorial",          "url": "https://www.postgresqltutorial.com/",                                 "platform": "gratuit",  "duration": "~10h"},
        ],
        "projects": [
            {"title": "Optimisation de requêtes",     "description": "Analyser et optimiser des requêtes lentes avec EXPLAIN ANALYZE, index, partitioning","difficulty": "avancé"},
        ],
    },

    "mongodb": {
        "weeks": 1,
        "category": "databases",
        "priority": 2,
        "prereqs": ["python"],
        "courses": [
            {"title": "MongoDB University (M001)",    "url": "https://learn.mongodb.com/learning-paths/introduction-to-mongodb",   "platform": "MongoDB",  "duration": "~10h"},
        ],
        "projects": [
            {"title": "API avec MongoDB",             "description": "API FastAPI avec MongoDB (motor async), CRUD complet avec indexation",              "difficulty": "intermédiaire"},
        ],
    },

    "redis": {
        "weeks": 0.5,
        "category": "databases",
        "priority": 2,
        "prereqs": ["python"],
        "courses": [
            {"title": "Redis University RU101",       "url": "https://university.redis.com/courses/ru101/",                        "platform": "Redis",    "duration": "~8h"},
        ],
        "projects": [
            {"title": "Cache Redis pour API",         "description": "Implémenter un cache Redis sur les endpoints lents de l'API FastAPI",               "difficulty": "intermédiaire"},
        ],
    },

    "snowflake": {
        "weeks": 1,
        "category": "databases",
        "priority": 2,
        "prereqs": ["sql", "data warehouse"],
        "courses": [
            {"title": "Snowflake Hands-On Essentials", "url": "https://learn.snowflake.com/en/courses/uni-essentials/",            "platform": "Snowflake","duration": "~6h"},
        ],
        "projects": [
            {"title": "Data Warehouse Snowflake",     "description": "Charger, transformer et requêter des données dans Snowflake avec dbt",              "difficulty": "avancé"},
        ],
    },

    
    # BI / VISUALIZATION
   

    "power bi": {
        "weeks": 1,
        "category": "bi",
        "priority": 2,
        "prereqs": ["sql"],
        "courses": [
            {"title": "Power BI Desktop (Microsoft Learn)", "url": "https://learn.microsoft.com/en-us/training/paths/create-use-analytics-reports-power-bi/", "platform": "Microsoft", "duration": "~10h"},
        ],
        "projects": [
            {"title": "Dashboard ventes Power BI",    "description": "Dashboard interactif avec DAX, slicers et visualisations sur dataset Superstore",   "difficulty": "intermédiaire"},
        ],
    },

    "tableau": {
        "weeks": 1,
        "category": "bi",
        "priority": 2,
        "prereqs": ["sql"],
        "courses": [
            {"title": "Tableau Public (gratuit)",     "url": "https://public.tableau.com/en-us/s/resources",                       "platform": "Tableau",  "duration": "~10h"},
        ],
        "projects": [
            {"title": "Dashboard COVID Tableau",      "description": "Visualiser les données COVID mondiales avec cartes, tendances et filtres",          "difficulty": "intermédiaire"},
        ],
    },

    
    # BACKEND / API
    

    "fastapi": {
        "weeks": 1,
        "category": "backend",
        "priority": 1,
        "prereqs": ["python"],
        "courses": [
            {"title": "FastAPI Documentation officielle", "url": "https://fastapi.tiangolo.com/tutorial/",                         "platform": "FastAPI",  "duration": "~10h"},
        ],
        "projects": [
            {"title": "API REST complète",            "description": "CRUD complet avec FastAPI, SQLAlchemy, JWT auth, tests avec pytest",                "difficulty": "intermédiaire"},
        ],
    },

    "rest api": {
        "weeks": 0.5,
        "category": "backend",
        "priority": 1,
        "prereqs": ["python"],
        "courses": [
            {"title": "REST API Design Best Practices", "url": "https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/", "platform": "gratuit", "duration": "~3h"},
        ],
        "projects": [
            {"title": "Consommer des APIs publiques", "description": "Intégrer 3 APIs REST différentes dans une application Python",                      "difficulty": "débutant"},
        ],
    },
}


# Ordre d'apprentissage recommandé par catégorie 

CATEGORY_ORDER = [
    "tools",           
    "languages",       
    "data_manipulation",
    "databases",       
    "devops",          
    "cloud",           
    "data_engineering",
    "ml",              
    "bi",              
    "backend",        
]


def get_skill_info(skill_name: str) -> Optional[dict]:
    return SKILL_KNOWLEDGE_BASE.get(skill_name.lower().strip())


def get_all_skills() -> list:
    return list(SKILL_KNOWLEDGE_BASE.keys())