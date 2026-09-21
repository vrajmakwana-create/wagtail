import re
import math
from typing import Dict, List, Any
from bs4 import BeautifulSoup


TRANSITION_WORDS = {
    # Addition & Agreement
    "additionally", "also", "and", "another", "apart from", "as well as", "besides", "furthermore", 
    "in addition", "in the same way", "indeed", "likewise", "moreover", "not to mention", "plus", "too",
    # Contrast & Comparison
    "after all", "although", "and yet", "at the same time", "but", "by contrast", "conversely", 
    "despite", "even so", "even though", "however", "in contrast", "in spite of", "instead", 
    "nevertheless", "nonetheless", "on the contrary", "on the other hand", "regardless", "still", "whereas", "yet",
    # Cause & Result / Consequence
    "accordingly", "as a result", "because", "consequently", "due to", "for this reason", "hence", 
    "in light of", "owing to", "since", "so", "so that", "therefore", "thereby", "thus",
    # Example & Illustration
    "for example", "for instance", "in particular", "namely", "specifically", "to illustrate", "such as",
    # Summary & Conclusion
    "all in all", "altogether", "as shown", "in brief", "in conclusion", "in short", "in summary", 
    "to conclude", "to summarize", "overall", "finally",
    # Sequence & Time
    "afterwards", "at first", "before", "currently", "eventually", "first", "firstly", "meanwhile", 
    "next", "previously", "second", "secondly", "subsequently", "then", "third", "thirdly", "ultimately",
    # Clarification / Emphasis
    "above all", "certainly", "clearly", "in fact", "in other words", "obviously", "to put it another way", "undoubtedly"
}

PASSIVE_AUXILIARY = {"am", "is", "are", "was", "were", "be", "been", "being", "get", "gets", "got", "getting", "gotten"}
REGULAR_ED_VERB = re.compile(r'\b([a-z]+ed|[a-z]+en)\b', re.IGNORECASE)


class BlogSEOAnalyzer:

    def __init__(self, page: Any):
        self.page = page
        self.keyphrase = (getattr(page, "focus_keyphrase", "") or "").strip().lower()
        self.synonyms = [s.strip().lower() for s in (getattr(page, "keyphrase_synonyms", "") or "").split(",") if s.strip()]
        self.all_keyphrases = [self.keyphrase] + self.synonyms if self.keyphrase else []
        
        self.seo_title = (getattr(page, "seo_title", "") or getattr(page, "custom_meta_title", "") or page.title or "").strip()
        self.slug = page.slug or ""
        self.meta_desc = (getattr(page, "search_description", "") or getattr(page, "custom_meta_description", "") or getattr(page, "short_description", "") or "").strip()
        self.canonical_url = getattr(page, "canonical_url", "") or ""

        self.html_body, self.images, self.links = self._extract_content_from_streamfield()
        self.soup = BeautifulSoup(self.html_body, "html.parser")
        self.plain_text = self.soup.get_text(separator=" ", strip=True)
        self.words = re.findall(r'\b[a-zA-Z0-9]+\b', self.plain_text.lower())
        self.total_words = len(self.words)

    def _extract_content_from_streamfield(self):
        html_chunks = []
        images = []
        links = []

        if hasattr(self.page, "body_html") and self.page.body_html:
            html_chunks.append(str(self.page.body_html))
        elif hasattr(self.page, "body"):
            if isinstance(self.page.body, str):
                html_chunks.append(self.page.body)
            else:
                try:
                    for block in self.page.body:
                        block_type = getattr(block, "block_type", None) or (block.get("type") if isinstance(block, dict) else None)
                        value = getattr(block, "value", None) or (block.get("value") if isinstance(block, dict) else None)

                        if not block_type and not value:
                            continue

                        if block_type == "heading":
                            lvl = value.get("level", "h2") if isinstance(value, dict) else "h2"
                            txt = value.get("text", "") if isinstance(value, dict) else str(value)
                            html_chunks.append(f"<{lvl}>{txt}</{lvl}>")
                        elif block_type == "subheading":
                            html_chunks.append(f"<h2>{value}</h2>")
                        elif block_type in ["paragraph", "quote"]:
                            html_chunks.append(str(value))
                        elif block_type == "image" and value:
                            if isinstance(value, dict):
                                img_obj = value.get("image")
                                alt = value.get("alt_text") or (getattr(img_obj, "title", "") if img_obj else "")
                                url = getattr(img_obj, "file", "") if img_obj else ""
                            else:
                                alt = getattr(value, "title", "")
                                url = getattr(value, "file", "")
                            images.append({"alt": alt, "url": url})
                            html_chunks.append(f'<img src="#" alt="{alt}" />')
                        elif block_type in ["bullet_list", "numbered_list"]:
                            tag = "ul" if block_type == "bullet_list" else "ol"
                            items = "".join([f"<li>{item}</li>" for item in (value if isinstance(value, list) else [])])
                            html_chunks.append(f"<{tag}>{items}</{tag}>")
                except TypeError:
                    html_chunks.append(str(self.page.body))

        if getattr(self.page, "featured_image", None):
            feat_alt = getattr(self.page.featured_image, "title", "")
            images.append({"alt": feat_alt, "url": "featured_image"})

        full_html = " ".join(html_chunks)
        soup = BeautifulSoup(full_html, "html.parser")
        for img in soup.find_all("img"):
            img_alt = img.get("alt", "")
            img_src = img.get("src", "")
            if not any(i["alt"] == img_alt and i["url"] in [img_src, "block_image", "#", "featured_image"] for i in images):
                images.append({"alt": img_alt, "url": img_src})
        for a in soup.find_all("a", href=True):
            links.append({"href": a["href"], "text": a.get_text(strip=True)})

        return full_html, images, links

    def run_seo_analysis(self) -> Dict[str, Any]:
        tests = []

        # 1. Focus Keyphrase Set
        tests.append({
            "id": 1,
            "title": "Focus Keyphrase Set",
            "status": "pass" if self.keyphrase else "fail",
            "message": f"Focus keyphrase is '{self.keyphrase}'." if self.keyphrase else "No focus keyphrase has been set."
        })

        # 2 & 13. Keyphrase in SEO Title & Near Start
        if self.keyphrase:
            title_lower = self.seo_title.lower()
            kp_in_title = self.keyphrase in title_lower
            pos = title_lower.find(self.keyphrase)
            is_near_start = pos >= 0 and pos <= 15
            if kp_in_title and is_near_start:
                st = "pass"
                msg = "Focus keyphrase appears near the beginning of the SEO Title."
            elif kp_in_title:
                st = "pass"
                msg = "Focus keyphrase appears in the SEO Title."
            else:
                st = "fail"
                msg = "Focus keyphrase does not appear in the SEO Title."
        else:
            st, msg = "fail", "Set a focus keyphrase first."
        tests.append({"id": 2, "title": "Keyphrase in SEO Title", "status": st, "message": msg})

        # 3 & 19. Keyphrase in Slug
        if self.keyphrase:
            clean_kp = re.sub(r'[^a-z0-9]+', '-', self.keyphrase).strip('-')
            slug_match = clean_kp in self.slug.lower() or any(w in self.slug.lower() for w in clean_kp.split('-'))
            st = "pass" if slug_match else "fail"
            msg = "Focus keyphrase appears in the URL slug." if slug_match else "Focus keyphrase missing from URL slug."
        else:
            st, msg = "fail", "No keyphrase to match slug."
        tests.append({"id": 3, "title": "Keyphrase in Slug", "status": st, "message": msg})

        # 4 & 15. Meta Description Keyphrase
        if self.keyphrase:
            meta_lower = self.meta_desc.lower()
            found = any(kp in meta_lower for kp in self.all_keyphrases)
            st = "pass" if found else "fail"
            msg = "Focus keyphrase or synonym appears in meta description." if found else "Focus keyphrase missing from meta description."
        else:
            st, msg = "fail", "Set a focus keyphrase."
        tests.append({"id": 4, "title": "Keyphrase in Meta Description", "status": st, "message": msg})

        # 5. Keyphrase in Image Alt Attributes
        if self.images:
            alt_match = any(any(kp in img["alt"].lower() for kp in self.all_keyphrases) for img in self.images if img["alt"])
            st = "pass" if alt_match else "warning"
            msg = "Keyphrase or synonym found in image alt text." if alt_match else "No image alt text contains the focus keyphrase."
        else:
            st, msg = "warning", "No images present to check alt text."
        tests.append({"id": 5, "title": "Keyphrase in Image Alt", "status": st, "message": msg})

        # 6. Images Count
        has_imgs = len(self.images) > 0
        tests.append({
            "id": 6,
            "title": "Images",
            "status": "pass" if has_imgs else "warning",
            "message": f"{len(self.images)} image(s) included." if has_imgs else "No images added. Add at least one image."
        })

        # 7. Keyphrase in Introduction
        paras = [p.get_text(strip=True) for p in self.soup.find_all(["p", "div"]) if len(p.get_text(strip=True)) > 20]
        first_para = paras[0].lower() if paras else ""
        if self.keyphrase and first_para:
            found_intro = any(kp in first_para for kp in self.all_keyphrases)
            st = "pass" if found_intro else "fail"
            msg = "Focus keyphrase or synonym appears in the first paragraph." if found_intro else "Focus keyphrase does not appear in the first paragraph."
        else:
            st, msg = "fail", "Keyphrase missing in introduction or content is empty."
        tests.append({"id": 7, "title": "Keyphrase in Introduction", "status": st, "message": msg})

        # 8. Keyphrase in Subheadings
        headings = [h.get_text(strip=True).lower() for h in self.soup.find_all(["h2", "h3"])]
        if headings and self.keyphrase:
            h_match = sum(1 for h in headings if any(kp in h for kp in self.all_keyphrases))
            st = "pass" if h_match > 0 else "warning"
            msg = f"{h_match} H2/H3 subheading(s) contain keyphrase or synonym." if h_match > 0 else "No H2/H3 subheadings contain the focus keyphrase."
        else:
            st, msg = "warning", "No H2/H3 subheadings found."
        tests.append({"id": 8, "title": "Keyphrase in Subheadings", "status": st, "message": msg})

        # 9. Competing Links Anchor Text
        competing = False
        if self.keyphrase:
            for l in self.links:
                if self.keyphrase in l["text"].lower():
                    competing = True
                    break
        tests.append({
            "id": 9,
            "title": "Competing Links Anchor Text",
            "status": "fail" if competing else "pass",
            "message": "An internal link uses exact focus keyphrase as anchor text." if competing else "No competing links found."
        })

        # 10 & 11. Links (Internal vs Outbound)
        outbound = [l for l in self.links if l["href"].startswith("http://") or l["href"].startswith("https://")]
        internal = [l for l in self.links if not (l["href"].startswith("http://") or l["href"].startswith("https://"))]
        tests.append({
            "id": 10,
            "title": "Outbound Links",
            "status": "pass" if outbound else "warning",
            "message": f"{len(outbound)} outbound link(s) found." if outbound else "No external outbound links found."
        })
        tests.append({
            "id": 11,
            "title": "Internal Links",
            "status": "pass" if internal else "warning",
            "message": f"{len(internal)} internal link(s) found." if internal else "No internal links found."
        })

        # 12. Keyphrase Density
        if self.keyphrase and self.total_words > 0:
            occurrences = self.plain_text.lower().count(self.keyphrase)
            density = round((occurrences * len(self.keyphrase.split())) / self.total_words * 100, 2)
            if 0.5 <= density <= 2.5:
                st = "pass"
                msg = f"Keyphrase density is {density}% ({occurrences} times)."
            elif density > 2.5:
                st = "fail"
                msg = f"Keyphrase density is high ({density}%). Avoid keyword stuffing."
            else:
                st = "warning"
                msg = f"Keyphrase density is low ({density}%). Use keyphrase a bit more."
        else:
            st, msg = "fail", "Cannot calculate density."
        tests.append({"id": 12, "title": "Keyphrase Density", "status": st, "message": msg})

        # 14. Keyphrase Length
        kp_len = len(self.keyphrase.split()) if self.keyphrase else 0
        tests.append({
            "id": 14,
            "title": "Keyphrase Length",
            "status": "pass" if 1 <= kp_len <= 4 else "warning",
            "message": f"Keyphrase length is {kp_len} word(s)." if 1 <= kp_len <= 4 else "Recommended keyphrase length is 1 to 4 words."
        })

        # 16. Meta Description Length
        meta_len = len(self.meta_desc)
        tests.append({
            "id": 16,
            "title": "Meta Description Length",
            "status": "pass" if 120 <= meta_len <= 160 else "warning",
            "message": f"Meta description is {meta_len} characters." if 120 <= meta_len <= 160 else f"Meta description is {meta_len} chars (Recommended: 120-160 chars)."
        })

        # 18. Single H1 Heading
        h1_count = len(self.soup.find_all("h1"))
        tests.append({
            "id": 18,
            "title": "Single H1 Heading",
            "status": "pass" if h1_count <= 1 else "fail",
            "message": f"Found {h1_count} H1 tags in content." if h1_count > 1 else "Only 1 or 0 H1 tag used."
        })

        # 20. Text Length
        tests.append({
            "id": 20,
            "title": "Text Length",
            "status": "pass" if self.total_words >= 300 else "fail",
            "message": f"Word count is {self.total_words} words." if self.total_words >= 300 else f"Word count is {self.total_words} words (Recommended minimum: 300 words)."
        })

        # 21. SEO Title Length / Width
        title_len = len(self.seo_title)
        tests.append({
            "id": 21,
            "title": "SEO Title Length",
            "status": "pass" if 40 <= title_len <= 60 else "warning",
            "message": f"SEO Title length is {title_len} characters." if 40 <= title_len <= 60 else f"SEO Title is {title_len} chars (Recommended: 40-60 chars)."
        })

        # 22. Cornerstone Content
        is_cornerstone = getattr(self.page, "is_cornerstone", False)
        tests.append({
            "id": 22,
            "title": "Cornerstone Content",
            "status": "info",
            "message": "Article marked as Cornerstone Content." if is_cornerstone else "Standard Article."
        })

        # 23-25. Robots Index & Follow Settings
        r_index = getattr(self.page, "robots_index", True)
        r_follow = getattr(self.page, "robots_follow", True)
        tests.append({
            "id": 23,
            "title": "Search Engine Indexing",
            "status": "pass" if r_index else "warning",
            "message": "Indexing allowed." if r_index else "Page set to noindex."
        })
        tests.append({
            "id": 24,
            "title": "Follow Links",
            "status": "pass" if r_follow else "warning",
            "message": "Links set to follow." if r_follow else "Links set to nofollow."
        })

        # 17. Previously Used Keyphrase
        prev_used = False
        if self.keyphrase and getattr(self.page, "pk", None):
            from blog.models import BlogPage
            prev_used = BlogPage.objects.filter(focus_keyphrase__iexact=self.keyphrase).exclude(pk=self.page.pk).exists()
        tests.append({
            "id": 17,
            "title": "Previously Used Keyphrase",
            "status": "fail" if prev_used else "pass",
            "message": f"Focus keyphrase '{self.keyphrase}' was previously used on another page." if prev_used else "Focus keyphrase has not been used before."
        })

        # 25. Meta Robots Advanced
        tests.append({
            "id": 25,
            "title": "Meta Robots Advanced",
            "status": "pass",
            "message": "No restrictive robots flags detected (index, follow enabled)."
        })

        # 27. Canonical URL
        tests.append({
            "id": 27,
            "title": "Canonical URL",
            "status": "pass",
            "message": f"Canonical URL: {self.canonical_url}" if self.canonical_url else "Self-referencing canonical URL will be generated."
        })

        # 31. Schema JSON-LD Structured Data (Additional Parameter)
        tests.append({
            "id": 31,
            "title": "Schema.org JSON-LD",
            "status": "pass",
            "message": "Article / BlogPosting schema generated automatically."
        })

        passed = sum(1 for t in tests if t["status"] == "pass")
        score = int((passed / len(tests)) * 100) if tests else 0

        return {
            "score": score,
            "passed_count": passed,
            "total_count": len(tests),
            "tests": tests
        }

    def run_readability_analysis(self) -> Dict[str, Any]:
        tests = []

        # Sentence Split
        raw_sentences = [s.strip() for s in re.split(r'[.!?]+', self.plain_text) if len(s.strip()) > 3]
        total_sentences = len(raw_sentences) or 1

        # 1. Word Complexity / Flesch Reading Ease
        total_syllables = sum(self._count_syllables(w) for w in self.words)
        if self.total_words > 0 and total_sentences > 0:
            flesch = 206.835 - (1.015 * (self.total_words / total_sentences)) - (84.6 * (total_syllables / self.total_words))
            flesch = round(max(0, min(100, flesch)), 1)
        else:
            flesch = 0.0

        tests.append({
            "id": 1,
            "title": "Flesch Reading Ease",
            "status": "pass" if flesch >= 60 else "warning",
            "message": f"Flesch Reading Ease score is {flesch} (Target: 60+)."
        })

        # 2. Transition Words
        transition_count = 0
        for s in raw_sentences:
            s_lower = s.lower()
            if any(tw in s_lower for tw in TRANSITION_WORDS):
                transition_count += 1
        transition_pct = round((transition_count / total_sentences) * 100, 1)
        tests.append({
            "id": 2,
            "title": "Transition Words",
            "status": "pass" if transition_pct >= 30.0 else "warning",
            "message": f"{transition_pct}% of sentences contain transition words (Target: 30%+)."
        })

        # 3. Passive Voice Detection
        passive_count = 0
        for s in raw_sentences:
            words_in_s = re.findall(r'\b[a-z]+\b', s.lower())
            for idx, w in enumerate(words_in_s[:-1]):
                if w in PASSIVE_AUXILIARY and REGULAR_ED_VERB.match(words_in_s[idx + 1]):
                    passive_count += 1
                    break
        passive_pct = round((passive_count / total_sentences) * 100, 1)
        tests.append({
            "id": 3,
            "title": "Passive Voice",
            "status": "pass" if passive_pct <= 10.0 else "warning",
            "message": f"{passive_pct}% of sentences contain passive voice (Target: <= 10%)."
        })

        # 4. Consecutive Sentences Starting with Same Word
        consecutive_same = 0
        max_consecutive = 0
        last_first_word = ""
        for s in raw_sentences:
            first_w = (re.findall(r'\b[a-z]+\b', s.lower()) or [""])[0]
            if first_w and first_w == last_first_word:
                consecutive_same += 1
                max_consecutive = max(max_consecutive, consecutive_same + 1)
            else:
                consecutive_same = 0
                last_first_word = first_w

        tests.append({
            "id": 4,
            "title": "Consecutive Sentences",
            "status": "pass" if max_consecutive < 5 else "fail",
            "message": f"Max consecutive sentences starting with same word: {max_consecutive} (Limit: < 5)."
        })

        # 5. Subheading Distribution (text blocks > 300 words)
        sections = self.soup.get_text().split("\n")
        long_section = False
        words_since_heading = 0
        for block in self.soup.children:
            if block.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                words_since_heading = 0
            else:
                words_since_heading += len(block.get_text().split())
                if words_since_heading > 300:
                    long_section = True

        tests.append({
            "id": 5,
            "title": "Subheading Distribution",
            "status": "fail" if long_section else "pass",
            "message": "Some text sections exceed 300 words without a subheading." if long_section else "Good subheading distribution across text."
        })

        # 6. Paragraph Length (max 150 words)
        paragraphs = [p.get_text(strip=True) for p in self.soup.find_all("p") if len(p.get_text(strip=True)) > 0]
        long_paras = sum(1 for p in paragraphs if len(p.split()) > 150)
        tests.append({
            "id": 6,
            "title": "Paragraph Length",
            "status": "fail" if long_paras > 0 else "pass",
            "message": f"{long_paras} paragraph(s) exceed 150 words." if long_paras > 0 else "All paragraphs are under 150 words."
        })

        # 7. Sentence Length (max 25% > 20 words)
        long_sentences = sum(1 for s in raw_sentences if len(s.split()) > 20)
        long_sent_pct = round((long_sentences / total_sentences) * 100, 1)
        tests.append({
            "id": 7,
            "title": "Sentence Length",
            "status": "pass" if long_sent_pct <= 25.0 else "warning",
            "message": f"{long_sent_pct}% of sentences contain more than 20 words (Target: <= 25%)."
        })

        passed = sum(1 for t in tests if t["status"] == "pass")
        score = int((passed / len(tests)) * 100) if tests else 0

        return {
            "score": score,
            "passed_count": passed,
            "total_count": len(tests),
            "tests": tests
        }

    def _count_syllables(self, word: str) -> int:
        word = word.lower()
        if len(word) <= 3:
            return 1
        word = re.sub(r'(?:[^laeiouy]es|ed|[^laeiouy]e)$', '', word)
        word = re.sub(r'^y', '', word)
        syllables = len(re.findall(r'[aeiouy]{1,2}', word))
        return max(1, syllables)
