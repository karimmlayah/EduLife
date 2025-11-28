#!/usr/bin/env python
"""
Script pour créer la table Like manuellement si la migration ne fonctionne pas
"""
import os
import sys
import django

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gl.settings')
django.setup()

from django.db import connection

def create_like_table():
    """Créer la table Like manuellement"""
    with connection.cursor() as cursor:
        # Créer la table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "UserApp_like" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "created_at" datetime NOT NULL,
                "post_id" bigint NOT NULL REFERENCES "UserApp_post" ("id") DEFERRABLE INITIALLY DEFERRED,
                "user_id" integer NOT NULL REFERENCES "UserApp_customuser" ("id") DEFERRABLE INITIALLY DEFERRED
            )
        """)
        
        # Créer les index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS "UserApp_like_post_id_idx" ON "UserApp_like" ("post_id")
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS "UserApp_like_user_id_idx" ON "UserApp_like" ("user_id")
        """)
        
        # Créer l'index unique
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS "UserApp_like_post_id_user_id_unique" 
            ON "UserApp_like" ("post_id", "user_id")
        """)
        
        # Marquer la migration comme appliquée
        cursor.execute("""
            INSERT OR IGNORE INTO "django_migrations" ("app", "name", "applied") 
            VALUES ('UserApp', '0011_like', datetime('now'))
        """)
        
        print("✅ Table UserApp_like créée avec succès!")
        print("✅ Index créés avec succès!")
        print("✅ Migration marquée comme appliquée!")

if __name__ == '__main__':
    try:
        create_like_table()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

