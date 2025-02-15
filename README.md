# Chatbot OpenRouter

Ce projet permet de générer automatiquement l'arborescence d'un projet en fonction d'une description fournie par l'utilisateur. Il utilise l'API OpenRouter pour obtenir la structure du projet au format JSON.

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

4. Créez un fichier `.env` à la racine du projet et ajoutez votre clé API OpenRouter :

    ```
    OPENROUTER_API_KEY=<votre_cle_api>
    ```

## Utilisation

1. Activez l'environnement Pipenv :

    ```
    pipenv shell
    ```

2. Lancez le script principal :

    ```
    python main.py
    ```

3. Lors de l'exécution, le script vous demandera :
    - Le chemin absolu où vous souhaitez créer l'arborescence du projet.
    - Une description de votre projet.

    Par exemple :

    - Chemin : `C:\Users\VotreNom\Documents\MonProjet`
    - Description : "Un projet de gestion de tâches avec un dossier backend et un dossier frontend, où chaque fichier initial est créé avec un placeholder."

Le programme générera la structure du projet en se basant sur votre description et créera les fichiers/dossiers correspondants à l'endroit indiqué.

## Remarques

- Assurez-vous que le chemin fourni lors de l'exécution est valide et accessible.
- Le script utilise des fonctions de normalisation et extraction pour garantir la validité du JSON retourné par l'API.
- N'hésitez pas à modifier les fichiers générés pour adapter le projet à vos besoins.
