# DocuMind AI

DocuMind AI est une application web complète d’analyse et de chat avec des documents s'appuyant sur une architecture RAG (*Retrieval-Augmented Generation*) moderne et performante. Elle permet d’importer des fichiers hétérogènes, de prévisualiser leur contenu, d'indexer automatiquement leur texte dans une base vectorielle, et d'interagir avec un assistant IA local pour poser des questions, générer des résumés, extraire des données clés ou comparer plusieurs documents.

---

## Fonctionnalités

- **Authentification & Sécurité** : Inscription, connexion JWT, isolation stricte des documents et données vectorielles par utilisateur (`user_id`).
- **Gestion des documents** : Import, téléchargement, inventaire et suppression complète (fichiers, métadonnées MongoDB et index Qdrant).
- **Prévisualisation interactive** : Aperçu dans le navigateur pour PDF, texte brut, Markdown et CSV ; téléchargement direct pour formats Office (DOCX, XLSX, PPTX).
- **Extraction & Normalisation avancées** :
  - Support de 7 formats : PDF, DOCX, XLSX, PPTX, CSV, TXT, MD.
  - Normalisation Unicode NFC (accents, ponctuation, support multilingue dont l'arabe).
  - Réparation automatique des césures de mots coupés en fin de ligne (`mot-\ncoupé` → `motcoupé`).
  - OCR Tesseract automatique (français + anglais) pour les pages PDF scannées ou sans texte vectorisé.
- **Pipeline RAG puissant** :
  - Découpage intelligent en chunks (~1 000 caractères, 150 caractères de chevauchement) avec conservation de la **page** et de la **localisation** pour un sourçage précis.
  - Génération d'embeddings par lots de 32 via le modèle multilingue `bge-m3` (1024 dimensions).
  - Indexation idempotente dans Qdrant (pas de doublons lors d'un réimport).
  - Reformulation contextuelle des questions de suivi à partir de l'historique conversationnel.
  - Filtrage par seuil de pertinence cosinus (`RELEVANCE_THRESHOLD = 0.25`) : si aucun extrait ne correspond, le service répond immédiatement sans appel LLM inutile.
  - Réponses sourcées avec références exactes (`[Source N]`, page, fichier, extrait).
- **Fonctionnalités documentaires avancées** :
  - **Résumé global** d'un document complet via un pipeline Map-Reduce.
  - **Extraction structurée** des informations clés (chiffres, entités, dates, conclusions).
  - **Comparaison multi-documents** avec analyse thématique des points communs et divergences.
  - **Explication ciblée** d'un passage précis, d'un chunk ou d'une page spécifique.

---

## Fonctionnement détaillé du pipeline RAG

Le cœur du système repose sur deux pipelines RAG principaux orchestrés par le service IA :

### 1. Pipeline d'Indexation (à l'import d'un document)

```
Fichier uploadé
      │
      ▼
1. Détection & Extraction (loaders spécifiques PDF, DOCX, XLSX, etc. + OCR si scan)
      │
      ▼
2. Nettoyage & Normalisation (Unicode NFC, suppression artefacts, réparation césures)
      │
      ▼
3. Découpage en chunks (RecursiveCharacterTextSplitter : 1 000 caractères, chevauchement 150)
   ↳ Conservation des métadonnées : page, localisation, chunk_index
      │
      ▼
4. Contrôle d'Idempotence (vérifie si le document est déjà indexé avec le même nombre de chunks)
      │
      ▼
5. Vectorisation par lots (batches de 32 avec le modèle d'embeddings bge-m3 via Ollama)
      │
      ▼
6. Upsert Qdrant (stockage dans documind_chunks avec index sur user_id et document_id)
```

### 2. Pipeline de Question-Réponse (Chat)

```
Question de l'utilisateur (+ Historique de conversation)
      │
      ▼
1. Reformulation autonome (le LLM reformule la question si un historique existe)
      │
      ▼
2. Embedding de la question (vectorisation de la requête avec bge-m3)
      │
      ▼
3. Recherche sémantique Qdrant (filtrage STRICT obligatoire par user_id)
      │
      ▼
4. Filtrage par seuil de pertinence cosinus (RELEVANCE_THRESHOLD = 0.25)
      ├─ Aucun chunk pertinent ?
      │  └── Réponse immédiate : « L'information ne figure pas dans les documents »
      │      (aucun appel LLM inutile, économie de ressources)
      │
      └─ Chunks pertinents trouvés ?
         │
         ▼
5. Construction du Prompt strict (contexte documentaire injecté avec balises [Source N])
         │
         ▼
6. Inférence LLM (qwen2.5:7b : consigne de ne rien inventer, réponse dans la langue de la question)
         │
         ▼
7. Réponse finale + Sources vérifiables (fichier, page, extrait exact)
```

### 3. Pipelines Documentaires Avancés

- **Résumé Map-Reduce** : Découpe le document, résume chaque section indépendamment (phase *Map*), puis consolide les résumés intermédiaires en une synthèse globale structurée (phase *Reduce*).
- **Extraction d'informations** : Parcourt les sections représentatives pour identifier de façon structurée les thèmes, dates, entités nommées et obligations.
- **Comparaison multi-documents** : Récupère les extraits de plusieurs documents (`document_id`) d'un même utilisateur et produit une analyse croisée thématique.
- **Explication ciblée** : Analyse en profondeur un extrait, une page ou un numéro de chunk précis avec son contexte adjacent.

---

## Architecture globale

```
[ Frontend React / Vite / Nginx ] (Port 3000 ou 5173)
             │
             ▼ (JWT Auth)
[ Backend Node.js / Express ] (Port 5000) ── MongoDB (Port 27017)
             │
             ▼ (X-Internal-Api-Key + X-User-Id)
[ AI Service Python / FastAPI ] (Port 8001 / 8000 interne)
      │                     │
      ▼                     ▼
[ Qdrant Vector DB ]   [ Ollama Local ] (Hôte : 11434)
  (Port 6333 / 6334)     ├─ LLM : qwen2.5:7b
                         └─ Embeddings : bge-m3 (1024 dim)
```

---

## Prérequis

1. **Docker Desktop** avec Docker Compose.
2. **[Ollama](https://ollama.com/)** installé et lancé sur la machine hôte.
3. Télécharger les deux modèles requis dans Ollama :

```cmd
ollama pull qwen2.5:7b
ollama pull bge-m3
```

- `qwen2.5:7b` : modèle de langage pour la génération de réponses, reformulations, résumés et analyses.
- `bge-m3` : modèle d'embeddings multilingue (1024 dimensions) haute précision pour l'indexation vectorielle RAG.

---

## Démarrage rapide avec Docker Compose

Depuis la racine du projet (`documind-ai`) :

1. Créez votre fichier d'environnement à partir de l'exemple :

   **Sous Windows (CMD) :**
   ```cmd
   copy .env.example .env
   ```

   **Sous PowerShell :**
   ```powershell
   Copy-Item .env.example .env
   ```

2. *(Optionnel en local)* Modifiez les clés secrètes `JWT_SECRET` et `AI_SERVICE_INTERNAL_API_KEY` dans `.env` si vous préparez un déploiement.

3. Lancez l'ensemble des conteneurs :

   ```cmd
   docker compose up -d --build
   ```

4. Rendez-vous sur [http://localhost:3000](http://localhost:3000) pour créer un compte et démarrer l'analyse de vos documents.

---

### Services et accès réseau

| Service | Port hôte | URL / Accès | Rôle |
|---|---|---|---|
| **Frontend** | `3000` | `http://localhost:3000` | Interface utilisateur React servie par Nginx |
| **Backend** | `5000` | `http://localhost:5000` | API Express (Auth JWT, gestion documents, MongoDB) |
| **Service IA** | `8001` | `http://localhost:8001` | API FastAPI RAG (LangChain, Qdrant, Ollama) |
| **MongoDB** | `27017` | `mongodb://localhost:27017` | Base de données principale (users, docs, chat history) |
| **Qdrant** | `6333` | `http://localhost:6333/dashboard` | Base vectorielle (`documind_chunks`) |

---

## API du Service IA (`ai-service`)

Consommée par le backend Node.js, sécurisée par les en-têtes `X-Internal-Api-Key` et `X-User-Id` :

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe (statut immédiat du service) |
| `GET` | `/health/ready` | Readiness probe (vérifie l'accès à Qdrant et aux modèles Ollama) |
| `POST` | `/documents` | Upload, nettoyage, chunking et indexation vectorielle RAG |
| `GET` | `/documents` | Liste les documents indexés pour l'utilisateur courant |
| `DELETE` | `/documents/{id}` | Supprime tous les vecteurs du document dans Qdrant |
| `POST` | `/documents/{id}/summary` | Résumé global du document (pipeline Map-Reduce) |
| `POST` | `/documents/{id}/extract-info`| Extraction structurée des données et points clés |
| `POST` | `/documents/{id}/explain` | Explication pédagogique d'un passage ou d'une page |
| `POST` | `/documents/extract` | Extraction brute du texte sans indexation (rétrocompatibilité) |
| `POST` | `/chat` | Question-Réponse RAG avec reformulation et sources |
| `POST` | `/compare` | Analyse comparative entre plusieurs documents |

---

## Développement local (sans Docker pour le service IA)

Si vous souhaitez exécuter ou déboguer le service IA directement sur votre machine Windows :

```cmd
cd C:\Users\Wiem\Desktop\documind-ai\ai-service
set PYTHONPATH=C:\Users\Wiem\Desktop\documind-ai\ai-service
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

Documentation interactive OpenAPI / Swagger disponible sur : `http://localhost:8000/docs` (en mode développement).

---

## Commandes utiles

```cmd
REM Voir l'état des conteneurs
docker compose ps

REM Consulter les logs en continu
docker compose logs -f ai-service
docker compose logs -f backend

REM Arrêter les services
docker compose down

REM Reconstruire uniquement le service IA après modification de code
docker compose up -d --build ai-service
```
