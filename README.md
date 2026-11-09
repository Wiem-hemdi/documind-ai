# DocuMind AI

DocuMind AI est une application web de gestion de documents. Elle permet de créer un compte, d’importer des fichiers, de consulter leur contenu original, d’extraire le texte et de poser des questions à un assistant IA. Les conversations sont conservées par document.

## Fonctionnalités

- Inscription, connexion et accès aux documents associés au compte.
- Import et suppression de documents.
- Prévisualisation du fichier original : PDF, texte, Markdown et CSV.
- Téléchargement de l’original pour les formats Office non prévisualisés dans le navigateur.
- Extraction de texte pour PDF, DOCX, XLSX, PPTX, CSV, TXT et MD.
- OCR Tesseract en français et en anglais pour les pages de PDF scannés ou sans texte extractible.
- Questions à l’assistant sur un document, avec historique conservé dans MongoDB.

Formats acceptés à l’import : PDF, DOCX, XLSX, PPTX, CSV, TXT et MD. La limite d’import du frontend/backend est de 20 Mo par fichier.

## Prérequis

- Docker Desktop avec Docker Compose.
- [Ollama](https://ollama.com/) installé et démarré sur la machine hôte pour utiliser les réponses IA.
- Le modèle configuré, `qwen2.5:7b` par défaut. Téléchargement :

  ```powershell
  ollama pull qwen2.5:7b
  ```

L’extraction du texte et l’aperçu PDF ne nécessitent pas Ollama. Les questions à l’assistant, elles, en ont besoin.

## Démarrage avec Docker

Depuis la racine du dépôt, créez le fichier d’environnement :

```powershell
Copy-Item .env.example .env
```

Pour un usage local, les valeurs d’exemple fonctionnent. Avant tout déploiement, remplacez `JWT_SECRET` et `AI_SERVICE_INTERNAL_API_KEY` dans `.env` par des valeurs secrètes uniques. La même valeur `AI_SERVICE_INTERNAL_API_KEY` est utilisée par le backend et le service IA.

Construisez et démarrez l’application :

```powershell
docker compose up -d --build
```

Ouvrez ensuite [http://localhost:3000](http://localhost:3000), créez un compte, puis importez un document.

### Services et adresses locales

| Service | Adresse depuis l’hôte | Rôle |
|---|---|---|
| Frontend | `http://localhost:3000` | Application web servie par Nginx |
| Backend | `http://localhost:5000` | API Node.js/Express |
| Service IA | `http://localhost:8001` | API FastAPI et extraction/OCR |
| MongoDB | `localhost:27017` | Comptes, documents et historique des conversations |
| Qdrant | `localhost:6333` | Base vectorielle du projet |

Le service IA écoute sur le port `8000` dans Docker, publié sur `8001` côté hôte pour éviter les conflits avec un service local déjà présent sur `8000`. Le frontend Docker transmet les requêtes à l’API via Nginx.

Vérification du service IA :

```powershell
curl.exe http://localhost:8001/health
```

La réponse attendue contient `"status":"ok"`. La vérification de disponibilité des dépendances est accessible sur `http://localhost:8001/health/ready`.

## Développement frontend avec Vite

Le frontend peut aussi être lancé hors Docker. Depuis la racine :

```powershell
npm --prefix frontend run dev
```

Vite est normalement disponible sur `http://localhost:5173`. Il transmet `/api` au backend local `http://127.0.0.1:5000` et `/ai-api` au service IA local `http://127.0.0.1:8001`. Il faut donc que le backend, MongoDB et le service IA soient démarrés.

`http://localhost:3000` et `http://localhost:5173` servent la même application, mais avec des modes différents : version Docker compilée sur le port 3000 et serveur de développement Vite sur le port 5173.

## Fonctionnement de l’assistant IA

Quand vous posez une question depuis la fenêtre d’un document, le flux est le suivant :

1. Le frontend envoie la question à l’API backend avec votre session.
2. Le backend vérifie que le document appartient à votre compte, récupère le fichier original et les 12 derniers messages de cette conversation, puis transmet le tout au service IA.
3. Le service IA extrait à nouveau le texte du fichier. Pour les pages PDF scannées, il utilise aussi l’OCR configuré plus bas.
4. Le texte du document, limité à 24 000 caractères, la question et l’historique récent sont envoyés au modèle Ollama sélectionné. Si le texte est tronqué, l’interface le signale : des informations situées plus loin dans le document peuvent ne pas être prises en compte.
5. La réponse et la question sont enregistrées dans MongoDB. L’historique complet est conservé par document; seuls les 12 derniers messages sont réutilisés comme contexte pour répondre à la question suivante.

Le modèle reçoit comme consigne de répondre en français en s’appuyant sur le texte transmis et de signaler clairement si la réponse n’y figure pas. Il peut néanmoins se tromper : vérifiez les réponses importantes dans le document original.

Ce flux de chat extrait le texte du document directement et ne fait pas de recherche vectorielle dans Qdrant. Qdrant est démarré par Compose, mais n’est pas utilisé pour sélectionner le contexte des questions dans ce flux.

### Configurer Ollama

Avec Docker Compose, le service IA contacte Ollama sur l’hôte à l’adresse `http://host.docker.internal:11434`. Assurez-vous qu’Ollama fonctionne et que le modèle par défaut est téléchargé :

```powershell
ollama pull qwen2.5:7b
```

Le modèle de conversation par défaut est `qwen2.5:7b`. Pour en choisir un autre, définissez `LLM_MODEL` dans le fichier `.env` à la racine, téléchargez ce modèle dans Ollama, puis recréez le service IA. Si Ollama écoute à une autre adresse, définissez aussi `OLLAMA_BASE_URL`.

```powershell
docker compose up -d --build ai-service
```

En configuration Docker locale par défaut, le modèle s’exécute sur votre machine via Ollama. Si vous configurez une URL Ollama distante, le texte du document et la question lui seront transmis. Le service IA retourne une erreur si Ollama est indisponible ou si le modèle configuré n’est pas prêt.

## OCR des PDF scannés

Tesseract et les données de langue française (`fra`) et anglaise (`eng`) sont installés dans l’image du service IA. L’OCR est déclenché automatiquement lorsqu’une page PDF contient peu ou pas de texte sélectionnable.

Après une modification du Dockerfile, des dépendances ou du code du service IA, reconstruisez-le :

```powershell
docker compose up -d --build ai-service
```

Les images importées séparément ne sont pas encore prises en charge pour l’OCR. Les PDF chiffrés ou protégés par mot de passe ne peuvent pas être lus.

## Historique et suppression

Les questions et réponses sont enregistrées dans MongoDB avec l’identifiant du compte et celui du document. Rouvrir un document recharge son historique. L’option **Vider l’historique** ne supprime que la conversation; la suppression du document efface le fichier et l’historique associé.

## Commandes utiles

```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f ai-service
docker compose logs -f frontend
docker compose down
```

`docker compose down` arrête et supprime les conteneurs, mais conserve les volumes de données. Ne lancez pas `docker compose down -v` sauf si vous souhaitez aussi supprimer les données persistées (documents, base MongoDB et Qdrant).

Vérifications frontend :

```powershell
npm --prefix frontend run lint
npm --prefix frontend run build
```
