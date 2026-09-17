from django.core.management.base import BaseCommand
from wagtail.models import Page
from home.models import HomePage
from blog.models import BlogPage, BlogCategory, BlogSubCategory, BlogComment, BlogLike


class Command(BaseCommand):
    help = "Copy all missing categories, subcategories, pages, comments, and likes from SQLite into PostgreSQL."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting SQLite -> PostgreSQL data transfer..."))

        # 0. Transfer Users
        self.transfer_users()

        # 1. Transfer Categories
        self.transfer_categories()

        # 2. Transfer Subcategories
        self.transfer_subcategories()

        # 3. Transfer missing BlogPages
        self.transfer_blog_pages()

        # 4. Transfer Comments
        self.transfer_comments()

        # 5. Transfer Likes
        self.transfer_likes()

        self.stdout.write(self.style.SUCCESS("--- SQLite -> PostgreSQL Transfer Complete! ---"))

    def transfer_users(self):
        from django.contrib.auth import get_user_model
        from core.models import UserProfile

        User = get_user_model()
        sqlite_users = User.objects.using("sqlite").all()
        created_count = 0
        for u in sqlite_users:
            pg_user = User.objects.using("default").filter(username=u.username).first()
            if not pg_user:
                pg_user = User.objects.using("default").create(
                    id=u.id,
                    username=u.username,
                    email=u.email,
                    password=u.password,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    is_staff=u.is_staff,
                    is_active=u.is_active,
                    is_superuser=u.is_superuser,
                    last_login=u.last_login,
                    date_joined=u.date_joined,
                )
                created_count += 1

            sqlite_profile = getattr(u, "profile", None)
            if sqlite_profile:
                pg_profile, _ = UserProfile.objects.using("default").get_or_create(user=pg_user)
                pg_profile.bio = sqlite_profile.bio
                pg_profile.profile_image = sqlite_profile.profile_image
                pg_profile.profile_image_url = sqlite_profile.profile_image_url
                pg_profile.save(using="default")

        self.stdout.write(f"Transferred {created_count} Users and UserProfiles to PostgreSQL.")

    def transfer_categories(self):
        sqlite_cats = BlogCategory.objects.using("sqlite").all()
        created_count = 0
        for cat in sqlite_cats:
            if not BlogCategory.objects.using("default").filter(slug=cat.slug).exists():
                BlogCategory.objects.using("default").create(
                    id=cat.id,
                    name=cat.name,
                    slug=cat.slug,
                    description=cat.description,
                )
                created_count += 1
        self.stdout.write(f"Transferred {created_count} new Categories to PostgreSQL.")

    def transfer_subcategories(self):
        sqlite_subcats = BlogSubCategory.objects.using("sqlite").select_related("category").all()
        created_count = 0
        for subcat in sqlite_subcats:
            parent_cat = BlogCategory.objects.using("default").filter(slug=subcat.category.slug).first()
            if parent_cat and not BlogSubCategory.objects.using("default").filter(slug=subcat.slug).exists():
                BlogSubCategory.objects.using("default").create(
                    id=subcat.id,
                    category=parent_cat,
                    name=subcat.name,
                    slug=subcat.slug,
                )
                created_count += 1
        self.stdout.write(f"Transferred {created_count} new Subcategories to PostgreSQL.")

    def transfer_blog_pages(self):
        sqlite_pages = BlogPage.objects.using("sqlite").select_related("category", "subcategory").all()
        
        # Get target parent container in PostgreSQL (Kreativespace WP Blogs or Home Page)
        pg_parent = Page.objects.using("default").filter(slug="kreativespace-wp-blogs").first()
        if not pg_parent:
            pg_parent = HomePage.objects.using("default").first()

        created_count = 0
        for b in sqlite_pages:
            if not BlogPage.objects.using("default").filter(slug=b.slug).exists():
                # Map category and subcategory
                cat_pg = BlogCategory.objects.using("default").filter(slug=b.category.slug).first() if b.category else None
                subcat_pg = BlogSubCategory.objects.using("default").filter(slug=b.subcategory.slug).first() if b.subcategory else None

                new_blog = BlogPage(
                    title=b.title,
                    slug=b.slug,
                    short_description=b.short_description,
                    body=b.body,
                    published_date=b.published_date,
                    author=b.author,
                    category=cat_pg,
                    subcategory=subcat_pg,
                    custom_meta_title=b.custom_meta_title,
                    custom_meta_description=b.custom_meta_description,
                    focus_keyphrase=b.focus_keyphrase,
                    keyphrase_synonyms=b.keyphrase_synonyms,
                    canonical_url=b.canonical_url,
                    is_cornerstone=b.is_cornerstone,
                    robots_index=b.robots_index,
                    robots_follow=b.robots_follow,
                    social_title=b.social_title,
                    social_description=b.social_description,
                )
                pg_parent.specific.add_child(instance=new_blog)
                new_blog.save_revision().publish()
                created_count += 1

        self.stdout.write(f"Transferred {created_count} new BlogPages to PostgreSQL.")

    def transfer_comments(self):
        sqlite_comments = BlogComment.objects.using("sqlite").select_related("blog").all()
        created_count = 0
        for c in sqlite_comments:
            pg_blog = BlogPage.objects.using("default").filter(slug=c.blog.slug).first()
            if pg_blog and not BlogComment.objects.using("default").filter(blog=pg_blog, name=c.name, message=c.message).exists():
                BlogComment.objects.using("default").create(
                    id=c.id,
                    blog=pg_blog,
                    name=c.name,
                    email=c.email,
                    message=c.message,
                    status=c.status,
                    created_at=c.created_at,
                )
                created_count += 1
        self.stdout.write(f"Transferred {created_count} Comments to PostgreSQL.")

    def transfer_likes(self):
        sqlite_likes = BlogLike.objects.using("sqlite").select_related("blog").all()
        created_count = 0
        for l in sqlite_likes:
            pg_blog = BlogPage.objects.using("default").filter(slug=l.blog.slug).first()
            if pg_blog and not BlogLike.objects.using("default").filter(blog=pg_blog, device_id=l.device_id).exists():
                BlogLike.objects.using("default").create(
                    id=l.id,
                    blog=pg_blog,
                    device_id=l.device_id,
                    created_at=l.created_at,
                )
                created_count += 1
        self.stdout.write(f"Transferred {created_count} Likes to PostgreSQL.")
