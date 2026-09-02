from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.contrib.table_block.blocks import TableBlock


class HeadingBlock(blocks.StructBlock):
    text = blocks.CharBlock(
        required=True,
        help_text="Enter heading text",
    )

    level = blocks.ChoiceBlock(
        choices=[
            ("h1", "Heading 1 (H1)"),
            ("h2", "Heading 2 (H2)"),
            ("h3", "Heading 3 (H3)"),
            ("h4", "Heading 4 (H4)"),
            ("h5", "Heading 5 (H5)"),
            ("h6", "Heading 6 (H6)"),
        ],
        default="h2",
        required=True,
        help_text="Select heading level",
    )

    class Meta:  # type: ignore[name-defined]
        icon = "title"
        label = "Heading"


class CodeBlock(blocks.StructBlock):
    language = blocks.ChoiceBlock(
        choices=[
            ("python", "Python"),
            ("javascript", "JavaScript / TypeScript"),
            ("html", "HTML"),
            ("css", "CSS"),
            ("json", "JSON"),
            ("bash", "Bash / Shell"),
            ("sql", "SQL"),
        ],
        default="python",
        help_text="Select programming language for syntax highlighting",
    )
    code = blocks.TextBlock(
        required=True,
        rows=10,
        help_text="Paste your code snippet here",
    )

    class Meta:  # type: ignore[name-defined]
        icon = "code"
        label = "Code Block"


class CalloutBlock(blocks.StructBlock):
    style = blocks.ChoiceBlock(
        choices=[
            ("info", "Info (Blue)"),
            ("success", "Success (Green)"),
            ("warning", "Warning (Yellow)"),
            ("danger", "Danger / Error (Red)"),
        ],
        default="info",
        help_text="Select callout alert style",
    )
    title = blocks.CharBlock(
        required=False,
        help_text="Callout Title (Optional)",
    )
    text = blocks.RichTextBlock(
        required=True,
        help_text="Callout Content",
    )

    class Meta:  # type: ignore[name-defined]
        icon = "warning"
        label = "Callout / Alert Box"


class BlogStreamBlock(blocks.StreamBlock):

    # TEXT BLOCKS
    heading = HeadingBlock()

    subheading = blocks.CharBlock(
        required=True,
        help_text="Add a subheading",
    )

    paragraph = blocks.RichTextBlock(
        required=True,
        help_text="Add paragraph content",
        features=[
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "bold",
            "italic",
            "strikethrough",
            "superscript",
            "subscript",
            "code",
            "link",
            "document-link",
            "ol",
            "ul",
            "blockquote",
            "hr",
            "image",
            "embed",
        ],
    )

    # TABLE & DATA
    table = TableBlock(
        help_text="Create a structured data table"
    )

    # LIST BLOCKS
    bullet_list = blocks.ListBlock(
        blocks.CharBlock(help_text="List item text"),
        icon="list-ul",
        label="Bullet List",
    )

    numbered_list = blocks.ListBlock(
        blocks.CharBlock(help_text="List item text"),
        icon="list-ol",
        label="Numbered List",
    )

    # MEDIA BLOCKS
    image = ImageChooserBlock(
        help_text="Upload or select an image"
    )

    embed = EmbedBlock(
        help_text="Embed YouTube, Vimeo, Twitter/X, or other media URLs"
    )

    # SPECIAL CONTENT
    quote = blocks.BlockQuoteBlock(
        help_text="Add a blockquote text"
    )

    code = CodeBlock()

    callout = CalloutBlock()

    divider = blocks.StaticBlock(
        admin_text="Horizontal divider"
    )

    class Meta:  # type: ignore[name-defined]
        icon = "folder-open-inverse"
        label = "Blog Content Stream"
