import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
from django.db.models import Q
from django.utils import timezone
from blog.models import BlogPage

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def publish_scheduled_blogs():
    try:
        # 1. Run Wagtail's built-in publish_scheduled command for approved revisions
        call_command("publish_scheduled")

        # 2. Check for any unpublished BlogPage where current time >= published_date (or go_live_at)
        now = timezone.now()

        due_blogs = BlogPage.objects.filter(live=False).filter(
            Q(published_date__isnull=False, published_date__lte=now) |
            Q(go_live_at__isnull=False, go_live_at__lte=now)
        )

        for blog in due_blogs:
            latest_rev = blog.get_latest_revision()
            if not latest_rev:
                latest_rev = blog.save_revision()

            # Publish revision
            blog.publish(latest_rev, skip_permission_checks=True)

            msg = f"[APScheduler] Automatically published blog '{blog.title}' (ID: {blog.id}) because current time ({now.strftime('%d %b %Y %H:%M:%S')}) reached published_date ({blog.published_date.strftime('%d %b %Y %H:%M:%S')})."
            print(msg)
            logger.info(msg)

    except Exception:
        logger.exception("Error executing publish_scheduled_blogs")


def start_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        publish_scheduled_blogs,
        trigger="interval",
        seconds=60,
        id="publish_scheduled_blogs",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.start()
    print("[APScheduler] Background scheduler started (checking every 10s).")