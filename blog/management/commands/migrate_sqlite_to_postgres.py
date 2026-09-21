import os
import json
import sqlite3
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections
from django.contrib.auth import get_user_model
from django.utils import timezone

from wagtail.models import Page
from home.models import HomePage
from blog.models import BlogPage, BlogCategory, BlogSubCategory, BlogComment, BlogLike
from core.models import UserProfile


class Command(BaseCommand):
    help = "Migrate all data (Users, Categories, Subcategories, Wagtail Blog Pages, Comments, and Likes) directly from SQLite into PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sqlite-file",
            default="db.sqlite3",
            help="Path to source SQLite database file (default: db.sqlite3)",
        )
        parser.add_argument(
            "--pg-dbname",
            default=os.getenv("POSTGRES_DB", os.getenv("DB_NAME", "")),
            help="PostgreSQL database name (can also set via POSTGRES_DB env variable)",
        )
        parser.add_argument(
            "--pg-user",
            default=os.getenv("POSTGRES_USER", os.getenv("DB_USER", "")),
            help="PostgreSQL database username",
        )
        parser.add_argument(
            "--pg-password",
            default=os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "")),
            help="PostgreSQL database password",
        )
        parser.add_argument(
            "--pg-host",
            default=os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "localhost")),
            help="PostgreSQL database host (default: localhost)",
        )
        parser.add_argument(
            "--pg-port",
            default=os.getenv("POSTGRES_PORT", os.getenv("DB_PORT", "5432")),
            help="PostgreSQL database port (default: 5432)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean existing blog pages and categories in target PostgreSQL DB before migrating.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the migration without modifying the target PostgreSQL database.",
        )

    def handle(self, *args, **options):
        sqlite_file = options["sqlite_file"]
        dry_run = options["dry_run"]
        clean = options["clean"]

        if not os.path.isabs(sqlite_file):
            sqlite_file = os.path.abspath(os.path.join(settings.BASE_DIR, sqlite_file))

        if not os.path.exists(sqlite_file):
            self.stderr.write(self.style.ERROR(f"SQLite database file not found: {sqlite_file}"))
            return

        # Setup PostgreSQL as default database if credentials provided
        pg_dbname = options["pg_dbname"]
        if pg_dbname:
            pg_config = settings.DATABASES["default"].copy()
            pg_config.update({
                "ENGINE": "django.db.backends.postgresql",
                "NAME": pg_dbname,
                "USER": options["pg_user"],
                "PASSWORD": options["pg_password"],
                "HOST": options["pg_host"],
                "PORT": options["pg_port"],
            })
            settings.DATABASES["default"] = pg_config
            connections["default"].close()
            self.stdout.write(self.style.SUCCESS(f"Connected Django to PostgreSQL ({pg_dbname}@{options['pg_host']})"))

        self.stdout.write(self.style.SUCCESS(f"--- Starting Data Migration: SQLite ({sqlite_file}) -> PostgreSQL ---"))
        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY-RUN MODE ENABLED ==="))

        # Open raw SQLite connection for reading source data
        sqlite_conn = sqlite3.connect(sqlite_file)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()

        try:
            # 1. Migrate Users & Profiles
            self.migrate_users(sqlite_cursor, dry_run)

            # 2. Migrate Categories & Subcategories
            cat_map, subcat_map = self.migrate_categories_and_subcategories(sqlite_cursor, clean, dry_run)

            # 3. Migrate Wagtail Blog Pages
            page_map = self.migrate_blog_pages(sqlite_cursor, cat_map, subcat_map, clean, dry_run)

            # 4. Migrate Comments
            self.migrate_comments(sqlite_cursor, page_map, clean, dry_run)

            # 5. Migrate Likes
            self.migrate_likes(sqlite_cursor, page_map, clean, dry_run)

            self.stdout.write(self.style.SUCCESS("--- SQLite to PostgreSQL Migration Complete! ---"))
        finally:
            sqlite_conn.close()

    def migrate_users(self, cursor, dry_run=False):
        self.stdout.write("1/5 Migrating Users & UserProfiles...")
        User = get_user_model()
        try:
            cursor.execute("SELECT id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined FROM auth_user")
            users = cursor.fetchall()
        except Exception:
            users = []

        migrated_count = 0
        for u in users:
            if dry_run:
                migrated_count += 1
                continue

            user_obj, created = User.objects.get_or_create(
                username=u["username"],
                defaults={
                    "id": u["id"],
                    "email": u["email"] or "",
                    "password": u["password"] or "",
                    "first_name": u["first_name"] or "",
                    "last_name": u["last_name"] or "",
                    "is_staff": bool(u["is_staff"]),
                    "is_active": bool(u["is_active"]),
                    "is_superuser": bool(u["is_superuser"]),
                },
            )
            if created:
                migrated_count += 1

            # Migrate profile if present in SQLite core_userprofile
            try:
                cursor.execute("SELECT bio, profile_image_url FROM core_userprofile WHERE user_id = ?", (u["id"],))
                prof = cursor.fetchone()
                if prof:
                    UserProfile.objects.get_or_create(
                        user=user_obj,
                        defaults={
                            "bio": prof["bio"] or "",
                            "profile_image_url": prof["profile_image_url"] or "",
                        },
                    )
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(f"   Processed {migrated_count} Users & UserProfiles."))

    def migrate_categories_and_subcategories(self, cursor, clean=False, dry_run=False):
        self.stdout.write("2/5 Migrating Categories & Subcategories...")
        cat_map = {}
        subcat_map = {}

        if clean and not dry_run:
            BlogSubCategory.objects.all().delete()
            BlogCategory.objects.all().delete()

        # Categories
        try:
            cursor.execute("SELECT id, name, slug, description, focus_keyphrase, seo_title, meta_description FROM blog_blogcategory")
            cats = cursor.fetchall()
        except Exception:
            cats = []

        for c in cats:
            if not dry_run:
                cat_obj = BlogCategory.objects.filter(id=c["id"]).first()
                if not cat_obj:
                    cat_obj = BlogCategory.objects.filter(slug=c["slug"]).first()
                if not cat_obj:
                    cat_obj = BlogCategory.objects.create(
                        id=c["id"],
                        name=c["name"],
                        slug=c["slug"],
                        description=c["description"] or "",
                        focus_keyphrase=c["focus_keyphrase"] or "",
                        seo_title=c["seo_title"] or "",
                        meta_description=c["meta_description"] or "",
                    )
                cat_map[c["id"]] = cat_obj
            else:
                cat_map[c["id"]] = c["name"]

        # Subcategories
        try:
            cursor.execute("SELECT id, category_id, name, slug, description, focus_keyphrase, seo_title, meta_description FROM blog_blogsubcategory")
            subcats = cursor.fetchall()
        except Exception:
            subcats = []

        for sc in subcats:
            if not dry_run:
                parent_cat = cat_map.get(sc["category_id"])
                if not parent_cat:
                    parent_cat = BlogCategory.objects.filter(id=sc["category_id"]).first()

                if parent_cat:
                    subcat_obj = BlogSubCategory.objects.filter(id=sc["id"]).first()
                    if not subcat_obj:
                        subcat_obj = BlogSubCategory.objects.filter(slug=sc["slug"]).first()
                    if not subcat_obj:
                        subcat_obj = BlogSubCategory.objects.create(
                            id=sc["id"],
                            category=parent_cat,
                            name=sc["name"],
                            slug=sc["slug"],
                            description=sc["description"] or "",
                            focus_keyphrase=sc["focus_keyphrase"] or "",
                            seo_title=sc["seo_title"] or "",
                            meta_description=sc["meta_description"] or "",
                        )
                    subcat_map[sc["id"]] = subcat_obj
            else:
                subcat_map[sc["id"]] = sc["name"]

        self.stdout.write(self.style.SUCCESS(f"   Processed {len(cats)} Categories and {len(subcats)} Subcategories."))
        return cat_map, subcat_map

    def migrate_blog_pages(self, cursor, cat_map, subcat_map, clean=False, dry_run=False):
        self.stdout.write("3/5 Migrating Wagtail Blog Pages...")
        page_map = {}

        try:
            cursor.execute("""
                SELECT p.id as page_id, p.title, p.slug, p.first_published_at, p.go_live_at, p.expire_at,
                       bp.short_description, bp.body, bp.published_date, bp.author,
                       bp.category_id, bp.subcategory_id, bp.focus_keyphrase,
                       bp.custom_meta_title, bp.custom_meta_description, bp.keyphrase_synonyms,
                       bp.canonical_url, bp.is_cornerstone, bp.robots_index, bp.robots_follow,
                       bp.social_title, bp.social_description
                FROM blog_blogpage bp
                INNER JOIN wagtailcore_page p ON bp.page_ptr_id = p.id
                ORDER BY p.id ASC
            """)
            pages = cursor.fetchall()
        except Exception:
            pages = []

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"   [Dry Run] Found {len(pages)} blog pages."))
            return page_map

        # Root page check
        target_root = Page.objects.filter(depth=1).first()
        if not target_root:
            self.stderr.write(self.style.ERROR("   Target PostgreSQL database has no root Wagtail Page (depth=1). Please run initial Wagtail migrations on target DB."))
            return page_map

        container_slug = "kreativespace-wp-blogs"
        target_container = Page.objects.filter(slug=container_slug).first()

        if not target_container:
            home_page = HomePage.objects.first()
            if home_page:
                target_container = home_page
            else:
                target_container = HomePage(title="Kreativespace WP Blogs", slug=container_slug)
                target_root.add_child(instance=target_container)
                target_container.save_revision().publish()

        if clean:
            existing_children = target_container.get_children()
            if existing_children.exists():
                self.stdout.write(f"   Cleaning {existing_children.count()} existing pages under target container in PostgreSQL...")
                for child in existing_children:
                    child.delete()

        migrated_count = 0
        for p in pages:
            existing = BlogPage.objects.filter(slug=p["slug"]).first()
            if existing:
                page_map[p["page_id"]] = existing
                continue

            cat_obj = cat_map.get(p["category_id"]) if p["category_id"] else None
            subcat_obj = subcat_map.get(p["subcategory_id"]) if p["subcategory_id"] else None

            # Parse StreamField JSON body safely
            body_val = p["body"]
            if body_val and isinstance(body_val, str):
                try:
                    body_val = json.loads(body_val)
                except Exception:
                    body_val = [{"type": "paragraph", "value": f"<p>{body_val}</p>"}]

            pub_dt = self.parse_dt(p["published_date"]) or timezone.now()

            unique_slug = p["slug"]
            counter = 1
            while Page.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{p['slug']}-{counter}"
                counter += 1

            new_blog = BlogPage(
                title=p["title"],
                slug=unique_slug,
                short_description=p["short_description"] or "",
                body=body_val or [],
                published_date=pub_dt,
                first_published_at=self.parse_dt(p["first_published_at"]) or pub_dt,
                author=p["author"] or "Admin",
                category=cat_obj,
                subcategory=subcat_obj,
                focus_keyphrase=p["focus_keyphrase"] or "",
                custom_meta_title=p["custom_meta_title"] or "",
                custom_meta_description=p["custom_meta_description"] or "",
                keyphrase_synonyms=p["keyphrase_synonyms"] or "",
                canonical_url=p["canonical_url"] or "",
                is_cornerstone=bool(p["is_cornerstone"]),
                robots_index=bool(p["robots_index"]),
                robots_follow=bool(p["robots_follow"]),
                social_title=p["social_title"] or "",
                social_description=p["social_description"] or "",
            )

            target_container.specific.add_child(instance=new_blog)
            new_blog.save_revision().publish()
            page_map[p["page_id"]] = new_blog
            migrated_count += 1

        self.stdout.write(self.style.SUCCESS(f"   Successfully migrated {migrated_count} BlogPages to PostgreSQL."))
        return page_map

    def migrate_comments(self, cursor, page_map, clean=False, dry_run=False):
        self.stdout.write("4/5 Migrating Comments...")
        try:
            cursor.execute("SELECT id, blog_id, name, email, message, parent_id, status, device_id, created_at FROM blog_blogcomment ORDER BY id ASC")
            comments = cursor.fetchall()
        except Exception:
            comments = []

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"   [Dry Run] Found {len(comments)} comments."))
            return

        if clean:
            BlogComment.objects.all().delete()

        comment_map = {}
        migrated_count = 0

        for c in comments:
            target_blog = page_map.get(c["blog_id"])
            if not target_blog:
                continue

            target_parent = comment_map.get(c["parent_id"]) if c["parent_id"] else None

            comment_obj, created = BlogComment.objects.get_or_create(
                id=c["id"],
                defaults={
                    "blog": target_blog,
                    "name": c["name"] or "Anonymous",
                    "email": c["email"] or "",
                    "message": c["message"] or "",
                    "parent": target_parent,
                    "status": c["status"] or "approved",
                    "device_id": c["device_id"] or "",
                },
            )
            comment_map[c["id"]] = comment_obj
            if created:
                migrated_count += 1

        self.stdout.write(self.style.SUCCESS(f"   Successfully migrated {migrated_count} Comments."))

    def migrate_likes(self, cursor, page_map, clean=False, dry_run=False):
        self.stdout.write("5/5 Migrating Likes...")
        try:
            cursor.execute("SELECT id, blog_id, device_id, created_at FROM blog_bloglike")
            likes = cursor.fetchall()
        except Exception:
            likes = []

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"   [Dry Run] Found {len(likes)} likes."))
            return

        if clean:
            BlogLike.objects.all().delete()

        migrated_count = 0
        for l in likes:
            target_blog = page_map.get(l["blog_id"])
            if not target_blog:
                continue

            _, created = BlogLike.objects.get_or_create(
                id=l["id"],
                defaults={
                    "blog": target_blog,
                    "device_id": l["device_id"],
                },
            )
            if created:
                migrated_count += 1

        self.stdout.write(self.style.SUCCESS(f"   Successfully migrated {migrated_count} Likes."))

    def parse_dt(self, dt_str):
        if not dt_str:
            return None
        if isinstance(dt_str, datetime):
            return dt_str if timezone.is_aware(dt_str) else timezone.make_aware(dt_str)
        try:
            dt_str = str(dt_str).split(".")[0]
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            return timezone.make_aware(dt)
        except Exception:
            return None
