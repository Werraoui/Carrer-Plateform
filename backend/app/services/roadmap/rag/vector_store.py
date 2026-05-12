import os
import logging
from typing import Optional

log = logging.getLogger("vector_store")

# Dossier de persistance ChromaDB
CHROMA_DB_PATH   = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "chroma_db")
COLLECTION_NAME  = "career_guidance"
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"   # Léger, rapide, multilingue correct

# Singletons — initialisés une seule fois au démarrage
_chroma_client     = None
_collection        = None
_embedding_function = None


# ─── Initialisation ───────────────────────────────────────────────────────────

def _get_embedding_function():
    """
    Charge le modèle d'embeddings sentence-transformers.
    Téléchargement automatique au premier appel (~80MB).
    Mis en cache ensuite.
    """
    global _embedding_function
    if _embedding_function is not None:
        return _embedding_function

    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        log.info(f"Modèle embeddings chargé : {EMBEDDING_MODEL}")
        return _embedding_function

    except ImportError:
        raise ImportError(
            "sentence-transformers non installé.\n"
            "Lancer : pip install sentence-transformers chromadb"
        )
    except Exception as e:
        raise RuntimeError(f"Impossible de charger le modèle d'embeddings : {e}")


def get_collection():
    global _chroma_client, _collection

    if _collection is not None:
        return _collection

    try:
        import chromadb

        os.makedirs(CHROMA_DB_PATH, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection    = _chroma_client.get_or_create_collection(
            name               = COLLECTION_NAME,
            embedding_function = _get_embedding_function(),
            metadata           = {"hnsw:space": "cosine"},  # Distance cosinus pour la similarité sémantique
        )

        log.info(f"ChromaDB initialisé : {CHROMA_DB_PATH}")
        log.info(f"Collection '{COLLECTION_NAME}' : {_collection.count()} documents")
        return _collection

    except ImportError:
        raise ImportError(
            "chromadb non installé.\n"
            "Lancer : pip install chromadb sentence-transformers"
        )
    except Exception as e:
        raise RuntimeError(f"Impossible d'initialiser ChromaDB : {e}")


# ─── Indexation ───────────────────────────────────────────────────────────────

def index_documents(documents: list[dict], batch_size: int = 100) -> int:
    if not documents:
        log.warning("Aucun document à indexer")
        return 0

    collection = get_collection()
    indexed    = 0

    log.info(f"Indexation de {len(documents)} documents (batches de {batch_size})...")

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]

        try:
            collection.upsert(
                ids        = [doc["id"]       for doc in batch],
                documents  = [doc["text"]     for doc in batch],
                metadatas  = [doc["metadata"] for doc in batch],
            )
            indexed += len(batch)
            log.info(f"  Batch {i // batch_size + 1} : {indexed}/{len(documents)} documents indexés")

        except Exception as e:
            log.error(f"Erreur indexation batch {i // batch_size + 1} : {e}")

    log.info(f"Indexation terminée : {indexed} documents dans ChromaDB")
    return indexed


def is_indexed() -> bool:
    """Vérifie si la collection contient déjà des documents."""
    try:
        collection = get_collection()
        return collection.count() > 0
    except Exception:
        return False


def get_stats() -> dict:
    """Retourne les statistiques de la collection."""
    try:
        collection = get_collection()
        count      = collection.count()

        # Compter par type de source
        kb_results = collection.get(
            where      = {"source": "knowledge_base"},
            include    = [],
        )
        scraper_results = collection.get(
            where      = {"source": "scraper"},
            include    = [],
        )

        return {
            "total_documents":    count,
            "knowledge_base_docs": len(kb_results["ids"]),
            "scraper_docs":        len(scraper_results["ids"]),
            "collection_name":     COLLECTION_NAME,
            "db_path":             CHROMA_DB_PATH,
            "embedding_model":     EMBEDDING_MODEL,
        }
    except Exception as e:
        return {"error": str(e)}


def reset_collection():
    global _chroma_client, _collection

    try:
        if _chroma_client is None:
            get_collection()

        _chroma_client.delete_collection(COLLECTION_NAME)
        _collection = None
        log.info(f"Collection '{COLLECTION_NAME}' supprimée")

        # Recréer vide
        get_collection()
        log.info("Collection recréée vide — prête pour réindexation")

    except Exception as e:
        log.error(f"Erreur reset collection : {e}")
        raise


# ─── Recherche vectorielle ────────────────────────────────────────────────────

def search(
    query:      str,
    n_results:  int            = 3,
    filter_by:  Optional[dict] = None,
) -> list[dict]:
    if not query or not query.strip():
        return []

    try:
        collection = get_collection()

        query_params = {
            "query_texts": [query],
            "n_results":   min(n_results, max(1, collection.count())),
            "include":     ["documents", "metadatas", "distances"],
        }

        if filter_by:
            query_params["where"] = filter_by

        results = collection.query(**query_params)

        # Reformater les résultats
        formatted = []
        if results["documents"] and results["documents"][0]:
            for text, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                formatted.append({
                    "text":      text,
                    "metadata":  metadata,
                    "distance":  round(distance, 4),
                    "relevance": round(1 - distance, 4),
                })

        return formatted

    except Exception as e:
        log.error(f"Erreur recherche ChromaDB : {e}")
        return []


# ─── Initialisation automatique ──────────────────────────────────────────────

def initialize_vector_store(csv_dir: str = None, force_reindex: bool = False) -> dict:
    from app.services.roadmap.rag.document_loader import load_all_documents

    if force_reindex:
        log.info("Réindexation forcée...")
        reset_collection()

    if is_indexed() and not force_reindex:
        stats = get_stats()
        log.info(
            f"ChromaDB déjà indexé : {stats['total_documents']} documents "
            f"(KB: {stats['knowledge_base_docs']}, Scraper: {stats['scraper_docs']})"
        )
        return stats

    log.info("Première initialisation — chargement et indexation des documents...")

    documents = load_all_documents(csv_dir=csv_dir)

    if not documents:
        log.warning("Aucun document chargé — ChromaDB vide")
        return {"total_documents": 0}

    indexed = index_documents(documents)
    stats   = get_stats()

    log.info(
        f"ChromaDB initialisé : {stats['total_documents']} documents "
        f"(KB: {stats['knowledge_base_docs']}, Scraper: {stats['scraper_docs']})"
    )
    return stats