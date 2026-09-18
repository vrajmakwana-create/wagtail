from wagtail.admin.panels import Panel


class SEOAnalysisPanel(Panel):
    """
    Custom Wagtail Admin Panel to display live SEO & Readability Analysis reports
    directly on the BlogPage editor page.
    """
    template_name = "blog/admin/seo_analysis_panel.html"

    class BoundPanel(Panel.BoundPanel):
        template_name = "blog/admin/seo_analysis_panel.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            instance = getattr(self, "instance", None)
            
            if instance and hasattr(instance, "get_seo_report"):
                try:
                    context["seo_report"] = instance.get_seo_report()
                    context["readability_report"] = instance.get_readability_report()
                except Exception as e:
                    context["seo_report"] = None
                    context["readability_report"] = None
                    context["error"] = str(e)
            else:
                context["seo_report"] = None
                context["readability_report"] = None
                
            return context

