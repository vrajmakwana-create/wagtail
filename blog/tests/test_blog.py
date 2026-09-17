from django.test import TestCase
from rest_framework.test import APIClient
from blog.models import BlogPage, BlogCategory, BlogSubCategory
from blog.seo_analyzer import BlogSEOAnalyzer


class BlogCategorySubCategoryTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.category = BlogCategory.objects.create(
            name="Technology",
            slug="technology",
            description="Technology related articles"
        )
        self.subcategory = BlogSubCategory.objects.create(
            category=self.category,
            name="Python",
            slug="python"
        )

    def test_string_uuid_generated(self):
        self.assertEqual(len(self.category.id), 36)
        self.assertEqual(len(self.subcategory.id), 36)
        self.assertIsInstance(self.category.id, str)
        self.assertIsInstance(self.subcategory.id, str)

    def test_category_list_api_includes_subcategories(self):
        response = self.client.get("/api/blogs/categories/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["code"], 200)
        self.assertTrue(len(data["result"]) >= 1)

        category_item = next(c for c in data["result"] if c["slug"] == "technology")
        self.assertEqual(category_item["name"], "Technology")
        self.assertEqual(category_item["description"], "Technology related articles")
        self.assertEqual(len(category_item["subcategories"]), 1)
        self.assertEqual(category_item["subcategories"][0]["name"], "Python")
        self.assertEqual(category_item["subcategories"][0]["id"], self.subcategory.id)

    def test_subcategory_list_api(self):
        response = self.client.get("/api/blogs/subcategories/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["code"], 200)
        self.assertTrue(len(data["result"]) >= 1)
        python_sub = next(s for s in data["result"] if s["slug"] == "python")
        self.assertEqual(python_sub["slug"], "python")

    def test_auto_category_population_from_subcategory(self):
        page = BlogPage(
            title="Auto Category Test",
            slug="auto-category-test",
            subcategory=self.subcategory,
        )
        page.clean()
        self.assertEqual(page.category, self.category)

    def test_blogs_list_api_response_structure(self):
        from wagtail.models import Page
        root_page = Page.get_first_root_node()
        blog_page = BlogPage(
            title="Listing Test Blog",
            slug="listing-test-blog",
            category=self.category,
            subcategory=self.subcategory,
            focus_keyphrase="test keyphrase",
            keyphrase_synonyms="synonym1, synonym2",
            canonical_url="https://example.com/blog",
            is_cornerstone=True,
            robots_index=True,
            robots_follow=True,
            live=True,
        )
        root_page.add_child(instance=blog_page)

        response = self.client.get("/api/blogs/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get("results", [])
        self.assertTrue(len(results) >= 1)

        blog_item = results[0]
        # Excluded fields must NOT be present in response
        excluded_fields = [
            "focus_keyphrase",
            "keyphrase_synonyms",
            "canonical_url",
            "is_cornerstone",
            "robots_index",
            "robots_follow",
        ]
        for field in excluded_fields:
            self.assertNotIn(field, blog_item)

        # Category field must be simple category object without subcategories
        self.assertIn("category", blog_item)
        category_data = blog_item["category"]
        self.assertEqual(category_data["name"], "Technology")
        self.assertEqual(category_data["description"], "Technology related articles")
        self.assertNotIn("subcategories", category_data)

    def test_child_blog_page_category_and_subcategory_set_to_none(self):
        from wagtail.models import Page
        root_page = Page.get_first_root_node()

        parent_blog = BlogPage(
            title="Parent Blog",
            slug="parent-blog",
            subcategory=self.subcategory,
            live=True,
        )
        root_page.add_child(instance=parent_blog)
        parent_blog.clean()
        parent_blog.save()

        # Top-level blog page keeps category and subcategory
        self.assertEqual(parent_blog.category, self.category)
        self.assertEqual(parent_blog.subcategory, self.subcategory)

        child_blog = BlogPage(
            title="Child Blog",
            slug="child-blog",
            category=self.category,
            subcategory=self.subcategory,
            live=True,
        )
        parent_blog.add_child(instance=child_blog)
        child_blog.clean()
        child_blog.save()

        # Child blog page must reset category and subcategory to None
        self.assertIsNone(child_blog.category)
        self.assertIsNone(child_blog.subcategory)

    def test_blogs_list_api_search_filter(self):
        from wagtail.models import Page
        root_page = Page.get_first_root_node()

        blog1 = BlogPage(
            title="Django Optimization Techniques",
            slug="django-optimization-techniques",
            short_description="Learn how to optimize Django ORM queries.",
            author="Alice",
            live=True,
        )
        blog2 = BlogPage(
            title="Wagtail Headless Tutorial",
            slug="wagtail-headless-tutorial",
            short_description="Build modern APIs with Wagtail.",
            author="Bob",
            live=True,
        )
        root_page.add_child(instance=blog1)
        root_page.add_child(instance=blog2)

        # Test search matching title/description
        response = self.client.get("/api/blogs/?search=Django")
        self.assertEqual(response.status_code, 200)
        results = response.json().get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Django Optimization Techniques")

        # Test search parameter 'q'
        response_q = self.client.get("/api/blogs/?q=Headless")
        self.assertEqual(response_q.status_code, 200)
        results_q = response_q.json().get("results", [])
        self.assertEqual(len(results_q), 1)
        self.assertEqual(results_q[0]["title"], "Wagtail Headless Tutorial")





class BlogSEOAnalyzerTestCase(TestCase):

    def setUp(self):
        self.page = BlogPage(
            title="Comprehensive Guide to Wagtail CMS Development",
            slug="wagtail-cms-guide",
            short_description="Learn how to build high performance headless blogs using Wagtail CMS and Django.",
            focus_keyphrase="Wagtail CMS",
            keyphrase_synonyms="Wagtail CMS guide, Wagtail tutorial",
            author="Developer",
            body=[
                ("heading", {"text": "What is Wagtail CMS?", "level": "h2"}),
                ("paragraph", "<p>Wagtail CMS is an open-source Django content management system focused on flexibility and user experience. In this guide, we explore how Wagtail CMS simplifies website creation. Additionally, building blogs with Django and Wagtail CMS gives developers total control over headless APIs.</p>"),
                ("heading", {"text": "Key Benefits of Wagtail CMS", "level": "h2"}),
                ("paragraph", "<p>Furthermore, Wagtail CMS provides a customizable admin interface. For example, StreamField allows flexible structured content layout. Consequently, content editors can manage complex pages with ease.</p>")
            ]
        )

    def test_seo_analysis(self):
        analyzer = BlogSEOAnalyzer(self.page)
        report = analyzer.run_seo_analysis()
        self.assertIn("score", report)
        self.assertGreaterEqual(report["score"], 50)
        self.assertEqual(report["total_count"], 24)

    def test_readability_analysis(self):
        analyzer = BlogSEOAnalyzer(self.page)
        report = analyzer.run_readability_analysis()
        self.assertIn("score", report)
        self.assertGreaterEqual(report["score"], 60)


class UserAuthorDetailsTestCase(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        from core.models import UserProfile

        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="john_doe",
            first_name="John",
            last_name="Doe",
            password="password123",
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.bio = "Senior Technical Writer & Django Expert"
        self.profile.profile_image_url = "https://my-bucket.s3.us-east-1.amazonaws.com/media/profile_images/john.jpg"
        self.profile.save()

    def test_blog_detail_author_response(self):
        from wagtail.models import Page
        root_page = Page.get_first_root_node()

        blog_page = BlogPage(
            title="Author Test Blog",
            slug="author-test-blog",
            owner=self.user,
            live=True,
        )
        root_page.add_child(instance=blog_page)

        response = self.client.get(f"/api/blogs/{blog_page.slug}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        result = data.get("result", {})
        author_data = result.get("author", {})

        self.assertEqual(author_data.get("name"), "John Doe")
        self.assertEqual(author_data.get("bio"), "Senior Technical Writer & Django Expert")
        self.assertEqual(author_data.get("profile_image_url"), "https://my-bucket.s3.us-east-1.amazonaws.com/media/profile_images/john.jpg")


class BlogCommentsAndLikesTestCase(TestCase):

    def setUp(self):
        from wagtail.models import Page
        self.client = APIClient()
        root_page = Page.get_first_root_node()

        self.blog = BlogPage(
            title="Comments and Likes Test Blog",
            slug="comments-and-likes-test-blog",
            live=True,
        )
        root_page.add_child(instance=self.blog)

    def test_post_comment_initial_pending_status(self):
        url = f"/api/blogs/{self.blog.slug}/comments/"
        payload = {
            "name": "Alice",
            "email": "alice@example.com",
            "message": "This is a great blog post!",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["code"], 201)
        self.assertIn("awaiting admin approval", data["message"])
        self.assertEqual(data["result"]["status"], "pending")

        # Verify comment is created in DB with status pending
        from blog.models import BlogComment
        comment = BlogComment.objects.get(id=data["result"]["id"])
        self.assertEqual(comment.status, "pending")

        # GET comments endpoint should return empty results when comment is pending and no device_id provided
        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(len(get_resp.json()["results"]), 0)

    def test_pending_comment_visible_only_to_same_device_id(self):
        url = f"/api/blogs/{self.blog.slug}/comments/"
        payload = {
            "name": "Alice",
            "email": "alice@example.com",
            "message": "Pending comment with device_id",
            "device_id": "device_alice_123",
        }
        post_resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(post_resp.status_code, 201)

        # 1. GET without device_id -> should NOT show pending comment
        res_no_dev = self.client.get(url)
        self.assertEqual(len(res_no_dev.json()["results"]), 0)

        # 2. GET with different device_id -> should NOT show pending comment
        res_other_dev = self.client.get(f"{url}?device_id=device_bob_456")
        self.assertEqual(len(res_other_dev.json()["results"]), 0)

        # 3. GET with same device_id -> SHOULD show pending comment
        res_same_dev = self.client.get(f"{url}?device_id=device_alice_123")
        self.assertEqual(len(res_same_dev.json()["results"]), 1)
        self.assertEqual(res_same_dev.json()["results"][0]["device_id"], "device_alice_123")
        self.assertEqual(res_same_dev.json()["results"][0]["status"], "pending")

    def test_get_approved_comments_and_nested_replies(self):
        from blog.models import BlogComment

        # Create approved top-level comment
        comment1 = BlogComment.objects.create(
            blog=self.blog,
            name="Bob",
            email="bob@example.com",
            message="Top level comment",
            status=BlogComment.STATUS_APPROVED,
        )

        # Create approved reply to comment1
        reply1 = BlogComment.objects.create(
            blog=self.blog,
            name="Charlie",
            email="charlie@example.com",
            message="Reply to Bob",
            parent=comment1,
            status=BlogComment.STATUS_APPROVED,
        )

        # Create pending reply to reply1 (should not appear in GET replies)
        BlogComment.objects.create(
            blog=self.blog,
            name="Dave",
            email="dave@example.com",
            message="Pending reply",
            parent=reply1,
            status=BlogComment.STATUS_PENDING,
        )

        url = f"/api/blogs/{self.blog.slug}/comments/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], comment1.id)
        self.assertEqual(len(results[0]["replies"]), 1)
        self.assertEqual(results[0]["replies"][0]["id"], reply1.id)
        # Pending reply is not shown
        self.assertEqual(len(results[0]["replies"][0]["replies"]), 0)

    def test_toggle_like_api(self):
        url = f"/api/blogs/{self.blog.slug}/like/"
        payload = {"device_id": "device-12345"}

        # 1. First request -> Like
        res1 = self.client.post(url, data=payload, format="json")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1["result"]["is_liked"])
        self.assertEqual(data1["result"]["total_likes"], 1)

        # Verify BlogDetailAPIView shows likes_count and is_liked
        detail_url = f"/api/blogs/{self.blog.slug}/?device_id=device-12345"
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, 200)
        detail_data = detail_res.json()["result"]
        self.assertEqual(detail_data["likes_count"], 1)
        self.assertTrue(detail_data["is_liked"])

        # 2. Second request with same device_id -> Unlike (toggle off)
        res2 = self.client.post(url, data=payload, format="json")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertFalse(data2["result"]["is_liked"])
        self.assertEqual(data2["result"]["total_likes"], 0)

    def test_author_blogs_api(self):
        from django.contrib.auth import get_user_model
        from wagtail.models import Page

        User = get_user_model()
        user = User.objects.create_user(
            username="author_user",
            first_name="Vraj",
            last_name="Makwana",
            password="password",
        )

        root_page = Page.get_first_root_node()

        author_blog = BlogPage(
            title="Author Specific Blog",
            slug="author-specific-blog",
            owner=user,
            live=True,
        )
        root_page.add_child(instance=author_blog)

        url = f"/api/blogs/author/{user.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("author", data)
        self.assertEqual(data["author"]["id"], user.id)
        self.assertEqual(data["author"]["name"], "Vraj Makwana")
        results = data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Author Specific Blog")

    def test_subcategory_optional_on_top_level_blog_page(self):
        FormClass = BlogPage.get_edit_handler().get_form_class()

        # Verify BlogPageForm does NOT require subcategory for top level page
        form = FormClass()
        self.assertFalse(form.fields["subcategory"].required)

        # Verify BlogPageForm hides subcategory and does not require it for child blog page
        parent_page = BlogPage(title="Parent", slug="parent")
        child_form = FormClass(parent_page=parent_page)
        self.assertFalse(child_form.fields["subcategory"].required)

    def test_blog_page_without_subcategory_defaults_to_uncategorized(self):
        from wagtail.models import Page
        from blog.models import get_default_uncategorized_subcategory
        root_page = Page.get_first_root_node()
        blog_page = BlogPage(
            title="Uncategorized Test Blog",
            slug="uncategorized-test-blog",
        )
        root_page.add_child(instance=blog_page)

        uncategorized_sub = get_default_uncategorized_subcategory()
        self.assertIsNotNone(blog_page.subcategory)
        self.assertEqual(blog_page.subcategory, uncategorized_sub)
        self.assertEqual(blog_page.category, uncategorized_sub.category)
        self.assertEqual(blog_page.category.slug, "uncategorized")
        self.assertEqual(blog_page.subcategory.slug, "uncategorized")

    def test_published_date_future_date_validation(self):
        from django.utils import timezone
        from datetime import timedelta
        from django.core.exceptions import ValidationError
        from wagtail.models import Page

        root_page = Page.get_first_root_node()

        # Past date should raise ValidationError
        past_date = timezone.now() - timedelta(days=1)
        blog_page_past = BlogPage(
            title="Past Date Blog",
            slug="past-date-blog",
            published_date=past_date,
        )
        with self.assertRaises(ValidationError) as cm:
            blog_page_past.clean()
        self.assertIn("published_date", cm.exception.message_dict)

        # Future date should pass clean validation
        future_date = timezone.now() + timedelta(days=5)
        blog_page_future = BlogPage(
            title="Future Date Blog",
            slug="future-date-blog",
            published_date=future_date,
        )
        try:
            blog_page_future.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly for future published_date!")








