# Chatbot OpenRouter

Ce projet permet de générer automatiquement l'arborescence d'un projet en fonction d'une description fournie par l'utilisateur. Il utilise l'API OpenRouter pour obtenir la structure du projet au format JSON et Streamlit pour fournir une interface web interactive.

## Prérequis

- Python 3.8 ou supérieur
- Pipenv

## Installation

1. Clonez le dépôt ou copiez les fichiers du projet sur votre machine.
2. Ouvrez un terminal dans le dossier racine du projet.
3. Installez les dépendances via Pipenv :

    ```
    pipenv install
    ```

4. Si, malgré l'installation et l'activation de l'environnement avec `pipenv shell`, les dépendances ne semblent pas installées correctement, vous pouvez installer manuellement :
    
    ```
    pipenv install streamlit openai python-dotenv
    ```

5. Créez un fichier `.env` à la racine du projet et ajoutez votre clé API OpenRouter :

    ```
    OPENROUTER_API_KEY=<votre_cle_api>
    ```

    Vous pouvez obtenir votre clé API sur [OpenRouter](https://openrouter.ai/).

## Utilisation

1. Activez l'environnement Pipenv :

    ```
    pipenv shell
    ```

2. Lancez l'application Streamlit :

    ```
    streamlit run main.py
    ```

3. Dans l'interface web qui s'ouvre, vous pourrez :
    - Saisir le **chemin absolu** où vous souhaitez créer l'arborescence.
    - Entrer une **description** de votre projet dans la zone de texte.

4. Cliquez sur **"Créer le projet"** pour générer la structure initiale.  
   Si la structure générée ne correspond pas à vos attentes, cliquez sur **"Re-generer le projet"** pour supprimer le contenu du dossier existant et tenter une nouvelle génération avec le même prompt.

## Remarques

- Assurez-vous que le chemin fourni est valide et accessible.
- L'application utilise des placeholders pour indiquer l'état de la génération (en cours, succès ou erreur).
- Vous pouvez personnaliser et modifier les fichiers générés en fonction de vos besoins.
