import os
import re
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils import timezone

from wagtail.models import Page
from home.models import HomePage
from blog.models import (
    BlogPage,
    BlogCategory,
    BlogSubCategory,
    BlogComment,
    get_default_uncategorized_subcategory,
)


class Command(BaseCommand):
    help = "Import blog posts, categories, comments, and SEO meta from a WordPress SQL dump directly into SQLite with element-level StreamField mapping."

    def add_arguments(self, parser):
        parser.add_argument(
            "sql_file",
            nargs="?",
            default="wordpress.sql",
            help="Path to the wordpress.sql dump file (default: wordpress.sql)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the import without saving changes to the database.",
        )

    def handle(self, *args, **options):
        sql_file = options["sql_file"]
        dry_run = options["dry_run"]

        if not os.path.isabs(sql_file):
            sql_file = os.path.abspath(sql_file)

        if not os.path.exists(sql_file):
            self.stderr.write(self.style.ERROR(f"File not found: {sql_file}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Starting WordPress SQL -> SQLite migration from {sql_file}..."))
        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY-RUN MODE ENABLED ==="))

        # 1. Load MySQL dump into temporary SQLite DB in memory
        conn = self.load_sql_dump(sql_file)
        cursor = conn.cursor()

        # 2. Get or create WordPress parent container page
        parent_container = self.get_or_create_wordpress_parent(dry_run)

        # 3. Clean existing imported pages under parent container for fresh import if needed
        if not dry_run and parent_container:
            existing_children = parent_container.get_children()
            if existing_children.exists():
                self.stdout.write(f"Cleaning {existing_children.count()} existing pages under '{parent_container.title}' for fresh re-import...")
                for child in existing_children:
                    child.delete()

        # 4. Import Categories & Subcategories
        cat_map, subcat_map = self.import_categories(cursor, dry_run)

        # 5. Import Published Blog Posts with Element Mapping
        post_map = self.import_posts(cursor, parent_container, cat_map, subcat_map, dry_run)

        # 6. Import Comments
        self.import_comments(cursor, post_map, dry_run)

        self.stdout.write(self.style.SUCCESS("--- WordPress SQL -> SQLite Migration Complete! ---"))

    def clean_create_sql(self, sql):
        sql = re.sub(r"ENGINE\s*=\s*\w+", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"DEFAULT\s+CHARSET\s*=\s*[\w_]+", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"COLLATE\s*=\s*[\w_]+", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"COLLATE\s+[\w_]+", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"AUTO_INCREMENT\s*=\s*\d+", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"AUTO_INCREMENT", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"unsigned", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"USING\s+\w+", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"CHARACTER\s+SET\s+[\w_]+", "", sql, flags=re.IGNORECASE)

        sql = re.sub(r"bigint\(\d+\)", "INTEGER", sql, flags=re.IGNORECASE)
        sql = re.sub(r"int\(\d+\)", "INTEGER", sql, flags=re.IGNORECASE)
        sql = re.sub(r"tinyint\(\d+\)", "INTEGER", sql, flags=re.IGNORECASE)
        sql = re.sub(r"smallint\(\d+\)", "INTEGER", sql, flags=re.IGNORECASE)
        sql = re.sub(r"mediumint\(\d+\)", "INTEGER", sql, flags=re.IGNORECASE)
        sql = re.sub(r"datetime", "TEXT", sql, flags=re.IGNORECASE)
        sql = re.sub(r"timestamp", "TEXT", sql, flags=re.IGNORECASE)
        sql = re.sub(r"longtext", "TEXT", sql, flags=re.IGNORECASE)
        sql = re.sub(r"mediumtext", "TEXT", sql, flags=re.IGNORECASE)
        sql = re.sub(r"tinytext", "TEXT", sql, flags=re.IGNORECASE)
        sql = re.sub(r"double\(\d+,\d+\)", "REAL", sql, flags=re.IGNORECASE)
        sql = re.sub(r"float", "REAL", sql, flags=re.IGNORECASE)

        lines = sql.split("\n")
        new_lines = []
        for line in lines:
            l = line.strip().upper()
            if (
                l.startswith("KEY ")
                or l.startswith("UNIQUE KEY")
                or l.startswith("FULLTEXT KEY")
                or (l.startswith("PRIMARY KEY") and "(`" not in l)
                or l.startswith("SPATIAL KEY")
                or l.startswith("CONSTRAINT ")
            ):
                continue
            new_lines.append(line)

        cleaned_sql = "\n".join(new_lines)
        cleaned_sql = re.sub(r",\s*\)", "\n)", cleaned_sql)
        return cleaned_sql

    def load_sql_dump(self, sql_file):
        self.stdout.write("Parsing WordPress SQL dump into temporary SQLite database...")
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        with open(sql_file, "r", encoding="utf-8", errors="ignore") as f:
            statement = []
            for line in f:
                line_str = line.strip()
                if (
                    not line_str
                    or line_str.startswith("--")
                    or line_str.startswith("/*")
                    or line_str.startswith("LOCK TABLES")
                    or line_str.startswith("UNLOCK TABLES")
                ):
                    continue

                statement.append(line)
                if line_str.endswith(";"):
                    full_stmt = "".join(statement)
                    statement = []
                    stmt_upper = full_stmt.strip().upper()

                    if stmt_upper.startswith("CREATE TABLE"):
                        cleaned = self.clean_create_sql(full_stmt)
                        try:
                            cursor.execute(cleaned)
                        except Exception:
                            pass
                    elif stmt_upper.startswith("INSERT INTO"):
                        try:
                            cursor.execute(full_stmt)
                        except Exception:
                            try:
                                cleaned_insert = full_stmt.replace("\\\\", "\0SLASHSLASH\0")
                                cleaned_insert = cleaned_insert.replace("\\'", "''")
                                cleaned_insert = cleaned_insert.replace('\\"', '"')
                                cleaned_insert = cleaned_insert.replace("\\n", "\n")
                                cleaned_insert = cleaned_insert.replace("\\r", "\r")
                                cleaned_insert = cleaned_insert.replace("\0SLASHSLASH\0", "\\")
                                cursor.execute(cleaned_insert)
                            except Exception:
                                pass

        conn.commit()
        return conn

    def get_or_create_wordpress_parent(self, dry_run=False):
        if dry_run:
            return None

        root = Page.objects.get(depth=1)
        wp_parent = Page.objects.filter(slug="kreativespace-wp-blogs").first()
        if not wp_parent:
            wp_parent = HomePage.objects.filter(title__icontains="Kreativespace WP Blogs").first()

        if not wp_parent:
            self.stdout.write("Creating parent container page 'Kreativespace WP Blogs'...")
            wp_parent = HomePage(
                title="Kreativespace WP Blogs",
                slug="kreativespace-wp-blogs",
            )
            root.add_child(instance=wp_parent)
            wp_parent.save_revision().publish()
        else:
            wp_parent = wp_parent.specific

        self.stdout.write(self.style.SUCCESS(f"Parent Container Page: '{wp_parent.title}' (ID: {wp_parent.id})"))
        return wp_parent

    def import_categories(self, cursor, dry_run=False):
        self.stdout.write("Importing Categories and Subcategories...")
        cat_map = {}
        subcat_map = {}

        # Always fetch or initialize default Uncategorized category and subcategory
        default_subcat = None
        if not dry_run:
            default_subcat = get_default_uncategorized_subcategory()

        try:
            cursor.execute("""
                SELECT t.term_id, t.name, t.slug, tt.parent, tt.description
                FROM wp_terms t
                INNER JOIN wp_term_taxonomy tt ON t.term_id = tt.term_id
                WHERE tt.taxonomy = 'category'
            """)
            terms = cursor.fetchall()
        except Exception:
            terms = []

        top_terms = [t for t in terms if t[3] == 0]
        for term_id, name, slug, parent, desc in top_terms:
            cat_slug = slugify(slug or name)
            if not cat_slug:
                cat_slug = f"cat-{term_id}"

            if not dry_run:
                category = BlogCategory.objects.filter(slug=cat_slug).first()
                if not category:
                    category = BlogCategory.objects.create(
                        name=name.strip(),
                        slug=cat_slug,
                        description=desc or "",
                    )
                cat_map[term_id] = category
            else:
                cat_map[term_id] = name

        child_terms = [t for t in terms if t[3] != 0]
        for term_id, name, slug, parent_term_id, desc in child_terms:
            subcat_slug = slugify(slug or name)
            if not subcat_slug:
                subcat_slug = f"subcat-{term_id}"

            parent_cat = cat_map.get(parent_term_id)
            if not dry_run:
                if not isinstance(parent_cat, BlogCategory):
                    parent_cat = default_subcat.category if default_subcat else BlogCategory.objects.get_or_create(name="Uncategorized", slug="uncategorized")[0]
                    cat_map[parent_term_id] = parent_cat

                subcat = BlogSubCategory.objects.filter(slug=subcat_slug).first()
                if not subcat:
                    subcat = BlogSubCategory.objects.create(
                        category=parent_cat,
                        name=name.strip(),
                        slug=subcat_slug,
                        description=desc or "",
                    )
                subcat_map[term_id] = subcat
            else:
                subcat_map[term_id] = name

        self.stdout.write(self.style.SUCCESS(f"Processed {len(cat_map)} Categories and {len(subcat_map)} Subcategories."))
        return cat_map, subcat_map

    def parse_html_to_stream_blocks(self, html_content):
        """Map HTML elements directly to Wagtail StreamField blocks."""
        if not html_content or not html_content.strip():
            return []

        # Remove Gutenberg comments
        html_content = re.sub(r"<!--\s*/?wp:[^>]+-->", "", html_content)

        # Wrap raw text into paragraphs if no block tags found
        if "<p>" not in html_content and "<h" not in html_content and "<div" not in html_content:
            paragraphs = [f"<p>{p.strip()}</p>" for p in html_content.split("\n\n") if p.strip()]
            html_content = "".join(paragraphs)

        soup = BeautifulSoup(f"<div>{html_content}</div>", "html.parser")
        container = soup.find("div")

        blocks = []

        for element in container.children:
            if isinstance(element, NavigableString):
                clean_text = re.sub(r"[\s\xa0\u200b\u200e\u200f]+", "", str(element))
                if clean_text:
                    blocks.append({"type": "paragraph", "value": f"<p>{str(element).strip()}</p>"})
                continue

            tag_name = element.name.lower() if element.name else ""

            # 1. Heading Elements (h1, h2, h3, h4, h5, h6)
            if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                heading_text = element.get_text().strip()
                if heading_text:
                    blocks.append({
                        "type": "heading",
                        "value": {
                            "text": heading_text,
                            "level": tag_name,
                        }
                    })

            # 2. Blockquote Elements
            elif tag_name == "blockquote":
                quote_text = element.get_text().strip()
                if quote_text:
                    blocks.append({
                        "type": "quote",
                        "value": quote_text,
                    })

            # 3. Code Elements (<pre>, <code>)
            elif tag_name in ["pre", "code"]:
                code_text = element.get_text()
                if code_text and code_text.strip():
                    blocks.append({
                        "type": "code",
                        "value": {
                            "language": "python",
                            "code": code_text.strip(),
                        }
                    })

            # 4. Unordered Lists (<ul>)
            elif tag_name == "ul":
                list_items = [li.get_text().strip() for li in element.find_all("li") if li.get_text().strip()]
                if list_items:
                    blocks.append({
                        "type": "bullet_list",
                        "value": list_items,
                    })

            # 5. Ordered Lists (<ol>)
            elif tag_name == "ol":
                list_items = [li.get_text().strip() for li in element.find_all("li") if li.get_text().strip()]
                if list_items:
                    blocks.append({
                        "type": "numbered_list",
                        "value": list_items,
                    })

            # 6. Horizontal Rules (<hr>)
            elif tag_name == "hr":
                blocks.append({
                    "type": "divider",
                    "value": None,
                })

            # 7. Paragraph & General Container Elements (<p>, <div>, <section>, etc.)
            else:
                text_content = element.get_text()
                clean_text = re.sub(r"[\s\xa0\u200b\u200e\u200f]+", "", text_content)
                has_image = bool(element.find("img"))
                if clean_text or has_image:
                    blocks.append({
                        "type": "paragraph",
                        "value": str(element),
                    })

        return blocks

    def import_posts(self, cursor, parent_container, cat_map, subcat_map, dry_run=False):
        self.stdout.write("Importing Published Posts with element-level StreamField mapping...")
        post_map = {}

        user_map = {}
        try:
            cursor.execute("SELECT ID, display_name FROM wp_users")
            for u_id, name in cursor.fetchall():
                user_map[u_id] = name
        except Exception:
            pass

        meta_dict = {}
        try:
            cursor.execute("""
                SELECT post_id, meta_key, meta_value FROM wp_postmeta
                WHERE meta_key IN (
                    '_yoast_wpseo_title', '_yoast_wpseo_metadesc', '_yoast_wpseo_focuskw',
                    'rank_math_title', 'rank_math_description', 'rank_math_focus_keyword'
                )
            """)
            for post_id, mkey, mval in cursor.fetchall():
                if post_id not in meta_dict:
                    meta_dict[post_id] = {}
                meta_dict[post_id][mkey] = mval
        except Exception:
            pass

        post_terms = {}
        try:
            cursor.execute("""
                SELECT tr.object_id, t.term_id, tt.parent
                FROM wp_term_relationships tr
                INNER JOIN wp_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
                INNER JOIN wp_terms t ON tt.term_id = t.term_id
                WHERE tt.taxonomy = 'category'
            """)
            for post_id, term_id, parent_id in cursor.fetchall():
                if post_id not in post_terms:
                    post_terms[post_id] = []
                post_terms[post_id].append((term_id, parent_id))
        except Exception:
            pass

        cursor.execute("""
            SELECT ID, post_author, post_date, post_content, post_title, post_excerpt, post_name
            FROM wp_posts
            WHERE post_type = 'post' AND post_status = 'publish'
            ORDER BY post_date ASC
        """)
        posts = cursor.fetchall()

        default_subcat = None
        if not dry_run:
            default_subcat = get_default_uncategorized_subcategory()

        imported_count = 0
        for wp_id, author_id, pdate, content, title, excerpt, name in posts:
            if not title or not title.strip():
                title = f"WordPress Post #{wp_id}"

            blog_slug = slugify(name or title)
            if not blog_slug:
                blog_slug = f"post-{wp_id}"

            published_dt = None
            if pdate:
                try:
                    published_dt = datetime.strptime(str(pdate), "%Y-%m-%d %H:%M:%S")
                    published_dt = timezone.make_aware(published_dt)
                except Exception:
                    published_dt = timezone.now()
            else:
                published_dt = timezone.now()

            author_name = user_map.get(author_id, "Admin")
            short_desc = excerpt.strip() if excerpt and excerpt.strip() else self.clean_excerpt(content)

            # Map HTML elements to Wagtail StreamField blocks
            body_blocks = self.parse_html_to_stream_blocks(content)
            if not body_blocks:
                body_blocks = [{"type": "paragraph", "value": "<p>Content empty.</p>"}]

            pmeta = meta_dict.get(wp_id, {})
            custom_title = pmeta.get("_yoast_wpseo_title") or pmeta.get("rank_math_title") or ""
            custom_desc = pmeta.get("_yoast_wpseo_metadesc") or pmeta.get("rank_math_description") or ""
            keyphrase = pmeta.get("_yoast_wpseo_focuskw") or pmeta.get("rank_math_focus_keyword") or ""

            # Determine category and subcategory
            cat_obj = None
            subcat_obj = None
            p_terms = post_terms.get(wp_id, [])

            if p_terms and not dry_run:
                cats_in_post = [cat_map[tid] for tid, pid in p_terms if tid in cat_map and isinstance(cat_map[tid], BlogCategory)]
                subcats_in_post = [subcat_map[tid] for tid, pid in p_terms if tid in subcat_map and isinstance(subcat_map[tid], BlogSubCategory)]

                if subcats_in_post:
                    subcat_obj = subcats_in_post[0]
                    cat_obj = subcat_obj.category
                elif cats_in_post:
                    cat_obj = cats_in_post[0]
                    # Find a subcategory under this category if one exists
                    subcat_obj = BlogSubCategory.objects.filter(category=cat_obj).first()

            # If still no category or subcategory assigned, use Uncategorized fallback
            if not subcat_obj and not dry_run:
                subcat_obj = default_subcat
                cat_obj = default_subcat.category if default_subcat else None

            if not dry_run and parent_container:
                unique_slug = blog_slug
                counter = 1
                while Page.objects.filter(slug=unique_slug).exists():
                    unique_slug = f"{blog_slug}-{counter}"
                    counter += 1

                blog_page = BlogPage(
                    title=title.strip(),
                    slug=unique_slug,
                    short_description=short_desc[:500],
                    body=body_blocks,
                    published_date=published_dt,
                    first_published_at=published_dt,
                    author=author_name,
                    category=cat_obj,
                    subcategory=subcat_obj,
                    custom_meta_title=str(custom_title)[:255],
                    custom_meta_description=str(custom_desc)[:500],
                    focus_keyphrase=str(keyphrase)[:100],
                )

                parent_container.add_child(instance=blog_page)
                blog_page.save_revision().publish()
                post_map[wp_id] = blog_page

            imported_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {imported_count} Published Blog Posts!"))
        return post_map

    def import_comments(self, cursor, post_map, dry_run=False):
        self.stdout.write("Importing Comments...")
        try:
            cursor.execute("""
                SELECT comment_ID, comment_post_ID, comment_author, comment_author_email, comment_content, comment_parent, comment_date
                FROM wp_comments
                WHERE comment_approved = '1'
                ORDER BY comment_date ASC
            """)
            comments = cursor.fetchall()
        except Exception:
            comments = []

        comment_map = {}
        imported_comments = 0

        for c_id, post_id, author, email, content, parent_c_id, cdate in comments:
            if dry_run:
                imported_comments += 1
                continue

            blog_page = post_map.get(post_id)
            if not blog_page:
                continue

            parent_comment = comment_map.get(parent_c_id) if parent_c_id else None
            author_name = author.strip() if author and author.strip() else "Anonymous"
            author_email = email.strip() if email and email.strip() else "anonymous@example.com"

            comment = BlogComment.objects.create(
                blog=blog_page,
                name=author_name,
                email=author_email,
                message=content.strip() if content else "",
                parent=parent_comment,
                status=BlogComment.STATUS_APPROVED,
            )
            comment_map[c_id] = comment
            imported_comments += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_comments} Comments!"))

    def clean_excerpt(self, html_content):
        if not html_content:
            return ""
        text = re.sub(r"<[^>]+>", " ", html_content)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:450] + "..." if len(text) > 450 else text
